
from adroll.model import fixture_helpers as fh

from adroll.model import Session, events, STATUS_APPROVED, STATUS_COMPLETED, STATUS_REJECTED, STATUS_KICKED, STATUS_OPTIONAL, STATUS_DRAFT, errors, advertisers
from adroll import api, utils
from adroll.dotcom.tests import TestController

from datetime import datetime, timedelta

import formencode

class TestUser(TestController):
    
    def _get_u_adv_pix(self, admin=False):
        u = admin and fh.create_admin() or fh.create_user()
        adv = fh.create_advertisable(user=u)
        pix = fh.create_pixel(advertisable=adv)
        
        return u, adv, pix
    
    def test_edit_create_not_my_pixel(self):
        u, adv, pix = self._get_u_adv_pix()
        u2, adv2, pix2 = self._get_u_adv_pix()
        
        self.flush()
        
        assert len(pix.non_prospect_segments) == 0
        
        d = {
            'name': 'something',
            'type': advertisers.SEGMENT_TYPE_CONVERSION,
            'rule': '*/asdj/*',
            'duration': 90,
            'value': None,
            'payload': ''
        }
        
        assert self.throws_exception(lambda: api.segment.edit(u, u, pix2, **d), types=(errors.ClientException,))
    
    def test_edit_create_not_my_pixel_admin(self):
        u, adv, pix = self._get_u_adv_pix(admin=True)
        u2, adv2, pix2 = self._get_u_adv_pix()
        
        self.flush()
        
        assert len(pix.non_prospect_segments) == 0
        
        d = {
            'name': 'something',
            'type': advertisers.SEGMENT_TYPE_CONVERSION,
            'rule': '*/asdj/*',
            'duration': 90,
            'value': None,
            'payload': ''
        }
        
        segment, mode = api.segment.edit(u, u, pix2, **d)
        assert segment.eid
    
    def test_edit_all_fail(self):
        u, adv, pix = self._get_u_adv_pix()
        self.flush()
        
        assert len(pix.non_prospect_segments) == 0
        
        d = {
            'name': '',
            'type': 'f',
            'rule': '',
            'duration': None,
            'value': 3,
            'payload': ''
        }
        
        errs = 0
        try:
            api.segment.edit(u, u, pix, **d)
        except formencode.validators.Invalid, (e):
            errs = len(e.error_dict.keys())
        
        assert errs == 4
    
    def test_edit_edit(self):
        u, adv, pix = self._get_u_adv_pix()
        self.flush()
        
        assert len(pix.non_prospect_segments) == 0
        
        d = {
            'name': 'something',
            'type': advertisers.SEGMENT_TYPE_CONVERSION,
            'rule': '*/asdj/*',
            'duration': 90,
            'value': None,
            'payload': ''
        }
        
        segment, mode = api.segment.edit(u, u, pix, **d)
        
        eid = segment.eid
        
        #actual editing!
        d['rule'] = '*/blah*'
        
        segment, mode = api.segment.edit(u, u, pix, segment=segment, **d)
        
        seg_db = Session.query(advertisers.Segment).filter_by(eid=eid).first()
        assert segment.eid == eid
        assert mode == 'edit'
        assert seg_db.rule.rule == '*/blah*'
        assert seg_db.user_rule == '/blah*'
        
        #More editing. type change FAIL
        d['type'] = advertisers.SEGMENT_TYPE_SEGMENT
        
        assert self.throws_exception(lambda: api.segment.edit(u, u, pix, segment=segment, **d))
        
        #More editing. rule validation FAIL
        d['type'] = advertisers.SEGMENT_TYPE_CONVERSION
        d['rule'] = '*/blah|pipebad'
        
        assert 'rule' in self.throws_exception(lambda: api.segment.edit(u, u, pix, segment=segment, **d)).error_dict
    
    def test_edit_create(self):
        u, adv, pix = self._get_u_adv_pix()
        self.flush()
        
        assert len(pix.non_prospect_segments) == 0
        
        d = {
            'name': 'something',
            'type': advertisers.SEGMENT_TYPE_CONVERSION,
            'rule': '*/asdj/*',
            'duration': 90,
            'value': None,
            'payload': ''
        }
        
        segment, mode = api.segment.edit(u, u, pix, **d)
        
        self.refresh(pix)
        
        assert len(pix.non_prospect_segments) == 1
        seg = pix.non_prospect_segments[0]
        
        assert seg.eid == segment.eid
        assert d['name'] in seg.name
        assert seg.type == d['type']
        assert seg.rule.rule == '*/asdj/*'
        assert seg.user_rule == '/asdj/*'
        assert seg.duration_sec == d['duration'] * 24*3600
        assert seg.order == 1
        assert seg.conversion_value == 0
        
        #create another segment
        
        d['name'] = 'two'
        d['rule'] = '*/asdasdj/*'
        d['value'] = 2.44
        
        segment, mode = api.segment.edit(u, u, pix, **d)
        
        self.refresh(pix)
        
        assert len(pix.non_prospect_segments) == 2
        seg = Session.query(advertisers.Segment).filter_by(eid=segment.eid).first()
        
        assert seg.order == 1
        assert seg.conversion_value == 244.0
        
        #create another segment-segment
        
        d['name'] = 'three'
        d['rule'] = '*/asdasdjs/*'
        d['value'] = None
        d['type'] = advertisers.SEGMENT_TYPE_SEGMENT
        
        segment, mode = api.segment.edit(u, u, pix, **d)
        
        self.refresh(pix)
        
        assert len(pix.non_prospect_segments) == 3
        seg = Session.query(advertisers.Segment).filter_by(eid=segment.eid).first()
        
        assert seg.order == 3
        assert seg.type == advertisers.SEGMENT_TYPE_SEGMENT
        
        #must have unique name
        assert self.throws_exception(lambda: api.segment.edit(u, u, pix, **d))
    
    def test_reorder(self):
        u, adv, pix = self._get_u_adv_pix()
        
        segs = []
        segs.append(fh.create_segment(pixel=pix, type=advertisers.SEGMENT_TYPE_CONVERSION, rule=u'*/something/blah1/*', order=1))
        segs.append(fh.create_segment(pixel=pix, type=advertisers.SEGMENT_TYPE_CONVERSION, rule=u'*/something/blah2/*', order=2))
        segs.append(fh.create_segment(pixel=pix, type=advertisers.SEGMENT_TYPE_CONVERSION, rule=u'*/something/blah3/*', order=3))
        segs.append(fh.create_segment(pixel=pix, type=advertisers.SEGMENT_TYPE_CONVERSION, rule=u'*/something/blah4/*', order=4))
        segs.append(fh.create_segment(pixel=pix, type=advertisers.SEGMENT_TYPE_SEGMENT, rule=u'*/something/blah5/*', order=5))
        
        self.flush()
        
        segments = pix.non_prospect_segments
        segments.sort(key=lambda x: x.order)
        
        #test initial order is correct
        for i, s in enumerate(segments):
            assert s.eid == segs[i].eid
        
        segs = [segs[4], segs[1], segs[0], segs[3], segs[2]]
        
        order = ','.join([s.eid for s in segs])
        
        assert api.segment.reorder(u, u, pix, order)
        
        self.refresh(pix)
        
        segments = pix.non_prospect_segments
        segments.sort(key=lambda x: x.order)
        for i, s in enumerate(segments):
            assert s.eid == segs[i].eid
    
    def test_delete_cannot(self):
        u, adv, pix = self._get_u_adv_pix()
        seg = fh.create_segment(pixel=pix)
        
        self.flush()
        
        assert seg.is_active
        
        assert self.throws_exception(lambda: api.segment.deactivate(u, u, pix, seg))
        
        self.refresh(seg)
        
        assert seg.is_active
    
    def test_delete_admin_can(self):
        u, adv, pix = self._get_u_adv_pix(admin=True)
        seg = fh.create_segment(pixel=pix)
        
        self.flush()
        
        assert seg.is_active
        
        assert api.segment.deactivate(u, u, pix, seg)
        
        self.refresh(seg)
        
        assert not seg.is_active

