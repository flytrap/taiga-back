#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Created by flytrap
import datetime
# from ics import Event, Calendar
# from arrow import Arrow
# from dateutil import tz as dateutil_tz
from django.db.models import Q
from taiga.projects.userstories.models import UserStory
from taiga.projects.tasks.models import Task


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

    @classmethod
    def format_datetime(cls, item):
        """format datetime"""
        # return Arrow(item.year, item.month, item.day, item.hour, item.minute)

    # @classmethod
    # def get_event(cls, item):
    #     e = Event()
    #     e.name = item.subject
    #     e.begin = cls.format_datetime(item.estimated_start)
    #     e.end = cls.format_datetime(item.estimated_start)
    #     e.description = item.description
    #     return e

    @classmethod
    def get_ics(cls, user, start=None, end=None):
        pass
        # if start is None:
        #     start = cls.get_monday()
        # if end is None:
        #     end = cls.get_weekend()
        # userstories = cls.get_userstories(user, start, end)
        # tasks = cls.get_tasks(user, start, end)

        # c = Calendar(creator=user.username)
        # for usersotory in userstories:
        #     e = cls.get_event(usersotory)
        #     c.events.append(e)
        # for task in tasks:
        #     e = cls.get_event(task)
        #     c.events.append(e)
        # return c

    @classmethod
    def get_userstories(cls, user, start, end):
        userstories = UserStory.objects.filter(assigned_to=user).filter(
            (Q(estimated_start__lte=end) & Q(estimated_start__gte=start)) | (
                Q(estimated_end__lte=end) & Q(estimated_end__gte=start)))
        return userstories

    @classmethod
    def get_tasks(cls, user, start, end):
        tasks = Task.objects.filter(assigned_to=user).filter(
            (Q(estimated_start__lte=end) & Q(estimated_start__gte=start)) | (
                Q(estimated_end__lte=end) & Q(estimated_end__gte=start)))
        return tasks


class WeeklyObj(object):
    def __init__(self, user, start=None, end=None):
        self.user = user
        self.delta = datetime.timedelta(7)
        self.start = CalendarService.get_monday()
        self.end = CalendarService.get_weekend()
        self.check_time(start, end)
        self.weeklies = {}

    def check_time(self, start, end):
        if start:
            try:
                self.start = datetime.datetime.strptime(start, "%Y-%m-%d").date()
            except:
                pass
        if end:
            try:
                self.end = datetime.datetime.strptime(end, "%Y-%m-%d").date()
            except:
                pass

    def get_title(self):
        return '# weekly ({}->{})\n'.format(self.start, self.end)

    def get_weekly(self):
        tasks = CalendarService.get_tasks(self.user, self.start, self.end).order_by('estimated_start')
        userstories = CalendarService.get_userstories(self.user, self.start, self.end).order_by('estimated_start')
        for task in tasks:
            if task.user_story not in self.weeklies:
                self.weeklies[task.user_story] = []
            self.weeklies[task.user_story].append(task)
        for userstory in userstories:
            if userstory not in self.weeklies:
                self.weeklies[userstory] = []

    def get_result(self):
        content = self.get_title()
        self.get_weekly()
        for us, tasks in self.weeklies.items():
            for task in tasks:
                content += self.get_content(task, parent=us)
            else:
                content += self.get_content(us)
        return content

    @staticmethod
    def get_content(item, prefix='* ', parent=None):
        content = prefix
        if item.estimated_start and item.estimated_end:
            content += '({}->{})'.format(item.estimated_start.strftime('%m-%d %H:%M'),
                                         item.estimated_end.strftime('%m-%d %H:%M'))
        if parent:
            content += '{}:'.format(parent.subject)
        content += item.subject
        if item.description:
            content += ': {}'.format(item.description)
        if item.status:
            content += '-------->status: {}\n'.format(item.status.name)
        return content


if __name__ == '__main__':
    pass
