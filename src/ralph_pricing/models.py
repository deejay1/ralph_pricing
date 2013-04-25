# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.db import models as db
from django.utils.translation import ugettext_lazy as _

from mptt.models import MPTTModel, TreeForeignKey


PRICE_DIGITS = 16
PRICE_PLACES = 6


class Device(db.Model):
    name = db.CharField(verbose_name=_("name"), max_length=255)
    device_id = db.IntegerField(
        verbose_name=_("device id"),
        unique=True,
    )
    asset_id = db.IntegerField(
        verbose_name=_("asset id"),
        unique=True,
        null=True,
        blank=True,
        default=None,
    )
    is_virtual = db.BooleanField(verbose_name=_("is virtual"), default=False)
    is_blade = db.BooleanField(verbose_name=_("is blade"), default=False)
    slots = db.FloatField(verbose_name=_("slots"), default=0)

    class Meta:
        verbose_name = _("device")
        verbose_name_plural = _("devices")

    def __unicode__(self):
        return self.name


class ParentDevice(Device):
    class Meta:
        proxy = True


class Venture(MPTTModel):
    venture_id = db.IntegerField()
    name = db.CharField(
        verbose_name=_("name"),
        max_length=255,
        default='',
    )
    department = db.CharField(
        verbose_name=_("department name"),
        max_length=255,
        default='',
    )
    parent = TreeForeignKey(
        'self',
        null=True,
        blank=True,
        default=None,
        related_name=_('children'),
    )

    class Meta:
        verbose_name = _("venture")
        verbose_name_plural = _("ventures")

    class MPTTMeta:
        order_insertion_by = ['name']

    def __unicode__(self):
        return self.name


class DailyPart(db.Model):
    date = db.DateField()
    name = db.CharField(verbose_name=_("name"), max_length=255)
    pricing_device = db.ForeignKey(Device)
    asset_id = db.IntegerField()
    price = db.DecimalField(
        max_digits=PRICE_DIGITS,
        decimal_places=PRICE_PLACES,
        verbose_name=_("price"),
    )
    is_deprecated = db.BooleanField(
        verbose_name=_("is deprecated"),
        default=False,
    )

    class Meta:
        verbose_name = _("daily part")
        verbose_name_plural = _("daily parts")
        unique_together = ('date', 'asset_id')
        ordering = ('asset_id', 'pricing_device', 'date')

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.date)


class DailyDevice(db.Model):
    date = db.DateField()
    name = db.CharField(verbose_name=_("name"), max_length=255)
    pricing_device = db.ForeignKey(
        Device,
        verbose_name=_("pricing device"),
    )
    parent = db.ForeignKey(
        # Note: this is only relevant for blade and virtual servers.
        ParentDevice,
        verbose_name=_("parent"),
        related_name='child_set',
        null=True,
        blank=True,
        default=None,
        on_delete=db.SET_NULL,
    )
    price = db.DecimalField(
        max_digits=PRICE_DIGITS,
        decimal_places=PRICE_PLACES,
        verbose_name=_("price"),
        default=0,
    )
    pricing_venture = db.ForeignKey(
        Venture,
        verbose_name=_("venture"),
        null=True,
        blank=True,
        default=None,
        on_delete=db.SET_NULL,
    )
    is_deprecated = db.BooleanField(
        verbose_name=_("is deprecated"),
        default=False,
    )

    class Meta:
        verbose_name = _("daily device")
        verbose_name_plural = _("daily devices")
        unique_together = ('date', 'pricing_device')
        ordering = ('pricing_device', 'date')

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.date)


class UsageType(db.Model):
    name = db.CharField(verbose_name=_("name"), max_length=255, unique=True)

    class Meta:
        verbose_name = _("usage type")
        verbose_name_plural = _("usage types")

    def __unicode__(self):
        return self.name


class UsagePrice(db.Model):
    type = db.ForeignKey(UsageType, verbose_name=_("type"))
    price = db.DecimalField(
        max_digits=PRICE_DIGITS,
        decimal_places=PRICE_PLACES,
        verbose_name=_("price"),
    )
    start = db.DateField()
    end = db.DateField()

    class Meta:
        verbose_name = _("usage price")
        verbose_name_plural = _("usage prices")
        unique_together = [
            ('start', 'type'),
            ('end', 'type'),
        ]
        ordering = ('type', 'start')

    def __unicode__(self):
        return '{} ({}-{})'.format(self.type, self.start, self.end)


class DailyUsage(db.Model):
    date = db.DateField()
    pricing_venture = db.ForeignKey(
        Venture,
        verbose_name=_("venture"),
        null=True,
        blank=True,
        default=None,
        on_delete=db.SET_NULL,
    )
    pricing_device = db.ForeignKey(
        Device,
        verbose_name=_("pricing device"),
        null=True,
        blank=True,
        default=None,
        on_delete=db.SET_NULL,
    )
    value = db.FloatField(verbose_name=_("value"))
    type = db.ForeignKey(UsageType, verbose_name=_("type"))

    class Meta:
        verbose_name = _("daily usage")
        verbose_name_plural = _("daily usages")
        unique_together = ('date', 'pricing_device', 'type')
        ordering = ('pricing_device', 'type', 'date')

    def __unicode__(self):
        return '{} ({}-{})'.format(self.pricing_device, self.start, self.end)


class ExtraCostType(db.Model):
    name = db.CharField(verbose_name=_("name"), max_length=255, unique=True)

    class Meta:
        verbose_name = _("extra cost type")
        verbose_name_plural = _("extra cost types")

    def __unicode__(self):
        return self.name


class ExtraCost(db.Model):
    start = db.DateField()
    end = db.DateField()
    type = db.ForeignKey(ExtraCostType, verbose_name=_("type"))
    price = db.DecimalField(
        max_digits=PRICE_DIGITS,
        decimal_places=PRICE_PLACES,
        verbose_name=_("price"),
    )
    pricing_venture = db.ForeignKey(Venture, verbose_name=_("venture"))

    class Meta:
        verbose_name = _("extra cost")
        verbose_name_plural = _("extra costs")
        unique_together = [
            ('start', 'pricing_venture', 'type'),
            ('end', 'pricing_venture', 'type'),
        ]

    def __unicode__(self):
        return '{}/{} ({}-{})'.format(
            self.pricing_venture,
            self.type,
            self.start,
            self.end,
        )