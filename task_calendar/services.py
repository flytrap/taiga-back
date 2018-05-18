#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Created by flytrap
import datetime
import time
from ics import Event, Calendar
from arrow import Arrow
from django.db.models import Q
from django.conf import settings
from taiga.projects.userstories.models import UserStory
from taiga.projects.tasks.models import Task

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
    def get_event(cls, item):
        e = Event()
        status_name = item.status.name if item.status else 'undefined'
        ref_type, link = cls.get_type_link(item)
        e.name = '[{}] [{}] {}'.format(status_name, ref_type.upper(), item.subject)
        e.begin = cls.format_datetime(item.estimated_start)
        e.end = cls.format_datetime(item.estimated_end)
        e.description = '{}\nlink: {}'.format(item.description, link)
        return e

    @staticmethod
    def get_type_link(item):
        ref_type = 'task' if isinstance(item, Task) else 'us'
        link = 'http://{}/project/{}/{}/{}'.format(front_base_url, item.project.slug, ref_type, item.ref)
        return ref_type, link

    @classmethod
    def get_ics(cls, user, start=None, end=None):
        if start is None:
            start = cls.get_ago_day()
        userstories = cls.get_userstories(user, *cls.check_time(start, end))
        tasks = cls.get_tasks(user, start, end)

        c = Calendar(creator=user.username)
        weeklies = {}
        for task in tasks:
            if task.user_story not in weeklies:
                weeklies[task.user_story] = []
                e = cls.get_event(task.user_story)
                c.events.append(e)
            e = cls.get_event(task)
            c.events.append(e)
            weeklies[task.user_story].append(task)
        for userstory in userstories:
            if userstory not in weeklies:
                weeklies[userstory] = []
                e = cls.get_event(userstory)
                c.events.append(e)
        return c

    @classmethod
    def get_userstories(cls, user, start, end):
        userstories = UserStory.objects.filter(assigned_to=user)
        if start and end:
            userstories = userstories.filter(
                (Q(estimated_start__lte=end) & Q(estimated_start__gte=start)) | (
                        Q(estimated_end__lte=end) & Q(estimated_end__gte=start)))
        elif start:
            userstories = userstories.filter(Q(estimated_start__gte=start) | Q(estimated_end__gte=start))
        elif end:
            userstories = userstories.filter(Q(estimated_start__lte=end) | Q(estimated_end__lte=end))
        return userstories

    @classmethod
    def get_tasks(cls, user, start, end):
        tasks = Task.objects.filter(assigned_to=user)
        if start and end:
            tasks = tasks.filter(
                (Q(estimated_start__lte=end) & Q(estimated_start__gte=start)) | (
                        Q(estimated_end__lte=end) & Q(estimated_end__gte=start)))
        elif start:
            tasks = tasks.filter(Q(estimated_start__gte=start) | Q(estimated_end__gte=start))
        elif end:
            tasks = tasks.filter(Q(estimated_start__lte=end) | Q(estimated_end__lte=end))
        return tasks

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
    def __init__(self, user, start=None, end=None):
        self.user = user
        self.delta = datetime.timedelta(7)
        if not start:
            start = CalendarService.get_monday()
        if not end:
            end = CalendarService.get_weekend()
        self.start, self.end = CalendarService.check_time(start, end)

    def get_title(self):
        return '# 周报 \n * time: {} 至 {}\n * 第 {} 周\n'.format(self.start, self.end, time.strftime("%W"))

    def get_weekly(self):
        weeklies = {}
        tasks = CalendarService.get_tasks(self.user, self.start, self.end).order_by('estimated_start')
        userstories = CalendarService.get_userstories(self.user, self.start, self.end).order_by('estimated_start')
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
        content = '{} [{}] [{}] ['.format(prefix, status_name, ref_type.upper())
        if parent:
            content += '{}:'.format(parent.subject)
        content += item.subject
        if item.description:
            content += ': {}'.format(item.description)
        if hasattr(item, 'get_total_points'):
            points = item.get_total_points()
            if points is not None:
                content += '({})'.format(item.get_total_points())
        if item.estimated_start and item.estimated_end:
            content += '[{}->{}] '.format(item.estimated_start.strftime('%m-%d:%H'),
                                          item.estimated_end.strftime('%m-%d:%H'))
        content += ']({})\n'.format(link)
        return content


if __name__ == '__main__':
    pass
