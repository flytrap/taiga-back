#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Created by flytrap
from io import StringIO
from django.contrib.auth import get_user_model
from django.http.response import HttpResponse, StreamingHttpResponse

from taiga.base.api.viewsets import GenericViewSet
from taiga.base.decorators import list_route
from taiga.base import response
from .services import CalendarService, WeeklyObj

User = get_user_model()


class CalenderViewSet(GenericViewSet):
    def get_user(self):
        user_id = self.request.QUERY_PARAMS.get('user_id')
        user = User.objects.filter(id=user_id).first()
        return user

    @list_route(methods=["GET"])
    def ics(self, request):
        user = request.user
        if not request.user.is_authenticated:
            user = self.get_user()
            if not user:
                return response.Unauthorized()
        c = CalendarService.get_ics(user, *self.parser_params())
        f = StringIO()
        for line in c:
            f.writelines(line)
        f.seek(0, 0)
        resp = HttpResponse(f, content_type='text/calendar; charset=UTF-8')
        username = user.full_name if user.full_name else user.username
        resp['Content-Disposition'] = 'attachment; filename="taiga-{}.ics"'.format(username)
        return resp

    def perform_content_negotiation(self, request, force=True):
        return super(CalenderViewSet, self).perform_content_negotiation(request, force)

    @list_route(methods=["GET"])
    def weekly(self, request):
        if not request.user.is_authenticated:
            return response.Unauthorized()
        start, end = self.parser_params()
        user = self.get_user()
        user = user if user else request.user
        data = WeeklyObj(user, start, end).get_report()
        return response.Ok(data)

    def parser_params(self):
        start = self.request.QUERY_PARAMS.get('start')
        end = self.request.QUERY_PARAMS.get('end')
        return start, end
