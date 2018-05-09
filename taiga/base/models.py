#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Created by flytrap
from django.db import models


class BaseDateModel(models.Model):
    estimated_start = models.DateTimeField('estimated_start', null=True, blank=True)
    estimated_end = models.DateTimeField('estimated_end', null=True, blank=True)

    class Meta:
        abstract = True
