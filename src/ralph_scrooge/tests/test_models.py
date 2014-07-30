# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import decimal

from django.test import TestCase

from ralph_scrooge import models
from ralph_scrooge.tests.models import History, HistoricalHistory


class TestModels(TestCase):
    def test_device_model(self):
        device = models.Device(device_id=3)
        device.save()
        device = models.Device.objects.get(device_id=3)
        self.assertEquals(device.device_id, 3)

    def test_venture_model(self):
        venture = models.Venture(venture_id=3)
        venture.save()
        venture = models.Venture.objects.get(venture_id=3)
        self.assertEquals(venture.venture_id, 3)

    def test_dailypart_model(self):
        device = models.Device(device_id=2)
        device.save()
        part = models.DailyPart(
            asset_id=4,
            pricing_device=device,
            date=datetime.date(2013, 4, 25),
            name='ziew',
            price=5,
        )
        part.save()
        self.assertEquals(part.date, datetime.date(2013, 4, 25))
        self.assertEquals(part.pricing_device.device_id, 2)
        self.assertEquals(part.asset_id, 4)
        self.assertEquals(part.price, 5)

    def test_dailydevice_model(self):
        device = models.Device(device_id=2)
        device.save()
        daily = models.DailyDevice(
            pricing_device=device,
            date=datetime.date(2013, 4, 25),
            name='ziew',
        )
        daily.save()
        self.assertEquals(daily.date, datetime.date(2013, 4, 25))
        self.assertEquals(daily.pricing_device.device_id, 2)

    def test_usage_models(self):
        type_ = models.UsageType(name='ziew')
        type_.save()
        price = models.UsagePrice(
            type=type_,
            price=3,
            start=datetime.date(2013, 4, 24),
            end=datetime.date(2013, 4, 26),
        )
        price.save()
        usage = models.DailyUsage(
            date=datetime.date(2013, 4, 25),
            value=3,
            type=type_,
        )
        usage.save()
        self.assertEquals(usage.value, 3)
        self.assertEquals(usage.type, type_)
        self.assertEquals(price.price, 3)
        self.assertEquals(type_.name, 'ziew')

    def test_extra_cost_models(self):
        type_ = models.ExtraCostType(name='ziew')
        type_.save()
        venture = models.Venture(venture_id=3)
        venture.save()
        cost = models.ExtraCost(
            type=type_,
            monthly_cost=3,
            pricing_venture=venture,
        )
        cost.save()
        self.assertEquals(type_.name, 'ziew')
        self.assertEquals(venture.venture_id, 3)
        self.assertEquals(cost.type, type_)
        self.assertEquals(cost.monthly_cost, 3)
        self.assertEquals(cost.pricing_venture, venture)


class TestPrices(TestCase):
    def test_asset_count_price(self):
        day = datetime.date(2013, 4, 25)
        venture = models.Venture(venture_id=3)
        venture.save()
        device = models.Device(
            device_id=3,
            asset_id=5,
        )
        device.save()
        daily = models.DailyDevice(
            pricing_device=device,
            date=day,
            name='ziew',
            price='1337',
            pricing_venture=venture,
        )
        daily.save()
        subventure = models.Venture(venture_id=2, parent=venture)
        subventure.save()
        other_device = models.Device(
            device_id=2,
            asset_id=3,
        )
        other_device.save()
        other_daily = models.DailyDevice(
            pricing_device=other_device,
            date=day,
            name='ziew',
            price='833833',
            pricing_venture=subventure,
        )
        other_daily.save()
        count, price, cost = venture.get_assets_count_price_cost(day, day)
        self.assertEquals(count, 1)
        self.assertEquals(price, decimal.Decimal('1337'))
        count, price, cost = venture.get_assets_count_price_cost(
            day, day, True,
        )
        self.assertEquals(count, 2)
        self.assertEquals(price, decimal.Decimal('835170'))

    def test_usages_count_price(self):
        day = datetime.date(2013, 4, 25)
        venture = models.Venture(venture_id=3)
        venture.save()
        usage_type = models.UsageType(name='waciki')
        usage_type.save()
        daily_usage = models.DailyUsage(
            type=usage_type,
            value=32,
            date=day,
            pricing_venture=venture,
        )
        daily_usage.save()
        other_day = datetime.date(2013, 4, 24)
        daily_usage = models.DailyUsage(
            type=usage_type,
            value=32,
            date=other_day,
            pricing_venture=venture,
        )
        daily_usage.save()
        usage_price = models.UsagePrice(
            start=day,
            end=day,
            price=4,
            type=usage_type,
        )
        usage_price.save()
        count, price = venture.get_usages_count_price(day, day, usage_type)
        self.assertEquals(count, 32)
        self.assertEquals(price, decimal.Decimal('128'))
        day = datetime.date(2013, 4, 26)
        count, price = venture.get_usages_count_price(day, day, usage_type)
        self.assertEquals(count, 0)
        self.assertEquals(price, decimal.Decimal('0'))
        day = datetime.date(2013, 4, 24)
        count, price = venture.get_usages_count_price(day, day, usage_type)
        self.assertEquals(count, 32)
        self.assertIsNone(price)


class TestHistory(TestCase):
    def test_history_flow(self):
        current_now = datetime.datetime.now()
        obj = History(field1=11, field2='aa')
        obj.save()
        # check historical record
        self.assertEquals(obj.history.count(), 1)
        obj1 = obj.history.most_recent()
        self.assertEquals(obj1.field1, 11)
        self.assertEquals(obj1.field2, 'aa')

        history1 = obj.history.all()[:1].get()
        self.assertGreater(history1.active_from, current_now)
        self.assertEquals(history1.active_to, datetime.datetime.max)

        current_now = datetime.datetime.now()
        # change obj
        obj.field1 = 12
        obj.save()

        # check historical record
        self.assertEquals(obj.history.count(), 2)
        obj2 = obj.history.most_recent()
        self.assertEquals(obj2.field1, 12)
        self.assertEquals(obj2.field2, 'aa')

        history2, history1 = obj.history.all()[:2]
        self.assertEquals(history1.active_to, history2.active_from)
        self.assertEquals(history2.active_to, datetime.datetime.max)

    def test_history_without_changes(self):
        obj = History(field1=11, field2='aa')
        obj.save()

        # check historical record
        self.assertEquals(obj.history.count(), 1)
        obj.field1 = 11
        obj.save()

        self.assertEquals(obj.history.count(), 1)

    def test_history_delete(self):
        obj = History(field1=11, field2='aa')
        obj.save()
        obj_id = obj.pk
        # check historical record
        self.assertEquals(obj.history.count(), 1)

        obj.delete()

        self.assertEquals(HistoricalHistory.objects.count(), 1)
        history1 = HistoricalHistory.objects.all()[:1].get()
        self.assertEquals(history1.id, obj_id)
        self.assertLess(history1.active_to, datetime.datetime.now())


class TestModelDiff(TestCase):
    def test_obj_diff(self):
        obj = History(field1=11, field2='b')
        obj.save()

        # "changes without changes"
        obj.field1 = 11
        self.assertFalse(obj.has_changed)

        # real changes
        obj.field2 = 'vvv'
        self.assertTrue(obj.has_changed)
        self.assertEquals(obj.diff, {'field2': ('b', 'vvv')})

    def test_obj2dict(self):
        obj = History(field1=11, field2='b')
        self.assertEquals(obj._dict, {'field1': 11, 'field2': 'b', 'id': None})
