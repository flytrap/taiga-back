#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Created by flytrap
import datetime
import time
from ics import Event, Calendar
from ics.parse import ContentLine
from arrow import Arrow
from django.db.models import Q
from django.conf import settings
from taiga.projects.userstories.models import UserStory
from taiga.projects.tasks.models import Task
from taiga.projects.models import Project

front_base_url = getattr(settings, 'SITES', {}).get('front', {}).get('domain', '')


class CalendarService(object):
    @staticmethod
    def get_monday():
        today = datetime.date.today()
        monday_delta = datetime.timedelta(today.weekday())
        return today - monday_delta

    @staticmethod
    def get_weekend():
        today = datetime.date.today()
        weekend_delta = datetime.timedelta(6 - today.weekday())
        weekend = today + weekend_delta
        return weekend

    @staticmethod
    def get_ago_day(days=40):
        today = datetime.date.today()
        day_delta = datetime.timedelta(days)
        day = today - day_delta
        return day

    @classmethod
    def format_datetime(cls, item):
        """format datetime"""
        if not item:
            return
        new_time = item - datetime.timedelta(hours=8)
        return Arrow(new_time.year, new_time.month, new_time.day, new_time.hour, new_time.minute)

    @classmethod
    def get_event(cls, item, project_id=None):
        e = Event()
        status_name = item.status.name if item.status else 'undefined'
        ref_type, link = cls.get_type_link(item)
        e.name = '{} [{}]'.format(item.subject, status_name)
        start = cls.format_datetime(item.estimated_start)
        end = cls.format_datetime(item.estimated_end)
        if start and end:
            start = min(start, end)
            end = max(start, end)
        e.begin = start
        e.end = end
        if item.assigned_to and project_id:
            e.name = '[{}] '.format(item.assigned_to.full_name) + e.name
        e.description = '{}\nlink: {}'.format(item.description, link)
        return e

    @staticmethod
    def get_type_link(item):
        ref_type = 'task' if isinstance(item, Task) else 'us'
        link = 'http://{}/project/{}/{}/{}'.format(front_base_url, item.project.slug, ref_type, item.ref)
        return ref_type, link

    @classmethod
    def get_ics(cls, user, start=None, end=None, project_id=None):
        if start is None:
            start = cls.get_ago_day()
        start, end = cls.check_time(start, end)
        userstories = cls.get_userstories(user, start, end, project_id)
        tasks = cls.get_tasks(user, start, end, project_id)

        if project_id:
            project = cls.get_project(project_id)
            username = 'taiga-project_{}'.format(project.name)
        else:
            username = 'taiga-{}'.format(user.full_name if user.full_name else user.username)

        c = Calendar(creator=username)
        c._unused.append(ContentLine('X-WR-CALNAME', value=username))

        weeklies = {}
        for task in tasks:
            if task.user_story not in weeklies:
                weeklies[task.user_story] = []
                e = cls.get_event(task.user_story, project_id)
                c.events.append(e)
            e = cls.get_event(task, project_id)
            c.events.append(e)
            weeklies[task.user_story].append(task)
        for userstory in userstories:
            if userstory not in weeklies:
                weeklies[userstory] = []
                e = cls.get_event(userstory, project_id)
                c.events.append(e)
        return c

    @classmethod
    def get_project(cls, project_id):
        return Project.objects.filter(id=project_id).first()

    @classmethod
    def get_userstories(cls, user, start, end, project_id=None):
        if project_id:
            userstories = UserStory.objects.filter(project_id=project_id)
        else:
            userstories = UserStory.objects.filter(assigned_to=user)
        if start and end:
            userstories = userstories.filter(
                (Q(estimated_start__lte=end) & Q(estimated_start__gte=start)) | (
                        Q(estimated_end__lte=end) & Q(estimated_end__gte=start)))
        elif start:
            userstories = userstories.filter(Q(estimated_start__gte=start) | Q(estimated_end__gte=start))
        elif end:
            userstories = userstories.filter(Q(estimated_start__lte=end) | Q(estimated_end__lte=end))
        return userstories.order_by('estimated_start')

    @classmethod
    def get_tasks(cls, user, start, end, project_id=None):
        if project_id:
            tasks = Task.objects.filter(user_story__project_id=project_id)
        else:
            tasks = Task.objects.filter(assigned_to=user)
        if start and end:
            tasks = tasks.filter(
                (Q(estimated_start__lte=end) & Q(estimated_start__gte=start)) | (
                        Q(estimated_end__lte=end) & Q(estimated_end__gte=start)))
        elif start:
            tasks = tasks.filter(Q(estimated_start__gte=start) | Q(estimated_end__gte=start))
        elif end:
            tasks = tasks.filter(Q(estimated_start__lte=end) | Q(estimated_end__lte=end))
        return tasks.order_by('estimated_start')

    @staticmethod
    def check_time(start, end):
        if start:
            try:
                start = datetime.datetime.strptime(start, "%Y-%m-%d").date()
            except:
                pass
        if end:
            try:
                end = datetime.datetime.strptime(end, "%Y-%m-%d").date()
            except:
                pass
        return start, end


class WeeklyObj(object):
    def __init__(self, user, start=None, end=None, project_id=None):
        self.user = user
        self.delta = datetime.timedelta(7)
        self.project_id = project_id
        if not start:
            start = CalendarService.get_monday()
        if not end:
            end = CalendarService.get_weekend()
        self.start, self.end = CalendarService.check_time(start, end)

    def get_title(self):
        return '# 周报 \n * 负责人: {} \n * 时间: {} 至 {}\n * 第 {} 周\n'.format(
            self.user.full_name, self.start, self.end, time.strftime("%W"))

    def get_weekly(self):
        weeklies = {}
        tasks = CalendarService.get_tasks(self.user, self.start, self.end)
        userstories = CalendarService.get_userstories(self.user, self.start, self.end)
        for task in tasks:
            if task.user_story not in weeklies:
                weeklies[task.user_story] = []
            weeklies[task.user_story].append(task)
        for userstory in userstories:
            if userstory not in weeklies:
                weeklies[userstory] = []
        return weeklies

    def get_result(self):
        content = ''
        weeklies = self.get_weekly()
        for us, tasks in weeklies.items():
            for task in tasks:
                content += self.get_content(task, parent=us)
            else:
                content += self.get_content(us)
        return content

    def get_report(self):
        content = self.get_title()
        content += '## 本周任务: \n'
        content += self.get_result()

        self.start = self.end + datetime.timedelta(1)
        self.end = self.end + datetime.timedelta(7)
        plan = self.get_result()
        if plan:
            content += '## 下周计划: \n'
            content += plan
        return content

    @staticmethod
    def get_content(item, prefix='* ', parent=None):
        ref_type, link = CalendarService.get_type_link(item)
        status_name = item.status.name if item.status else 'undefined'
        content = '{} [{}] ['.format(prefix, status_name)
        if parent:
            content += '{}:'.format(parent.subject)
        content += item.subject
        content += ']({})'.format(link)
        if item.description:
            content += ': {}'.format(item.description)
        if hasattr(item, 'get_total_points'):
            points = item.get_total_points()
            if points is not None:
                content += '({}个番茄)  '.format(int(points))
        if item.estimated_start and item.estimated_end:
            content += '[{}到{}] '.format(item.estimated_start.strftime('%Y-%m-%d %H:%M'),
                                         item.estimated_end.strftime('%Y-%m-%d %H:%M'))
        content += '\n'
        return content


if __name__ == '__main__':
    pass
