from django.shortcuts import render

# Create your views here.
from taiga.base.api.viewsets import GenericViewSet
from taiga.base.decorators import list_route, detail_route
from taiga.base import response
from .services import CalendarService, WeeklyObj


class CalenderViewSet(GenericViewSet):
    @list_route(methods=["GET"])
    def ics(self, request):
        if not request.user.is_authenticated:
            return response.Unauthorized()
        CalendarService.get_ics(request.user)
        return response.Ok()

    @list_route(methods=["GET"])
    def weekly(self, request):
        if not request.user.is_authenticated:
            return response.Unauthorized()
        start, end = self.parser_params()
        data = WeeklyObj(request.user, start, end).get_result()
        return response.Ok(data)

    def parser_params(self):
        start = self.request.QUERY_PARAMS.get('start')
        end = self.request.QUERY_PARAMS.get('end')
        return start, end
