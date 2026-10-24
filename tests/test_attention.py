import copy
import json
import tempfile
import unittest
from pathlib import Path
from pocket.attention import SCHEMA, PUTER_FINGERPRINT, load, plan, record, save


def entry(id, when):
    return {'id': id, 'title': id[:5], 'url': 'https://swarmmemo.com/e/'+id,
            'created_on': when, 'status': 'open', 'follow_for': 'check a claim'}


class AttentionTests(unittest.TestCase):
    def setUp(self):
        self.ids = [f'{n:032x}' for n in range(1, 6)]
        self.data = {'schema': SCHEMA, 'threads': [entry(self.ids[0], '2026-09-01'),
                    entry(self.ids[1], '2026-09-02'), entry(self.ids[2], '2026-10-23'),
                    entry(self.ids[3], '2026-10-23')], 'visits': []}

    def test_two_historical_one_recent(self):
        chosen = plan(self.data, '2026-10-24')
        self.assertEqual([a['id'] for a in chosen['selected']], self.ids[:3])
        self.assertEqual(chosen['historic_selected'], 2)

    def test_no_endless_refresh_before_revisit(self):
        self.data['threads'][0]['last_read'] = '2026-10-24'
        self.data['threads'][0]['next_due'] = '2026-11-07'
        chosen = plan(self.data, '2026-10-24')
        self.assertNotIn(self.ids[0], [x['id'] for x in chosen['selected']])

    def test_first_read_is_baseline_not_announcement(self):
        thread = {'ok': True, 'data': {'root_id': self.ids[0], 'has_more': False},
                  'messages': [{'id': self.ids[0], 'text': 'initial'}]}
        updated, event = record(self.data, self.ids[0], thread, '2026-10-24')
        self.assertTrue(event['baseline'])
        self.assertEqual(event['new_ids'], [])
        self.assertEqual(updated['threads'][0]['next_due'], '2026-11-07')
        self.assertNotIn('fingerprints', self.data['threads'][0])

    def test_later_new_reply_edit_and_missing_are_separate(self):
        original = {'ok': True, 'data': {'root_id': self.ids[0]},
                    'messages': [{'id': self.ids[0], 'text': 'initial'},
                                 {'id': self.ids[4], 'text': 'old reply'}]}
        a, _ = record(self.data, self.ids[0], original, '2026-10-24')
        updated = copy.deepcopy(original)
        updated['messages'] = [{'id': self.ids[0], 'text': 'edited'},
                               {'id': self.ids[3], 'text': 'new reply'}]
        b, event = record(a, self.ids[0], updated, '2026-11-08')
        self.assertEqual(event['new_ids'], [self.ids[3]])
        self.assertEqual(event['edited_ids'], [self.ids[0]])
        self.assertEqual(event['missing_ids'], [self.ids[4]])
        self.assertEqual(b['threads'][0]['next_due'], '2026-11-15')

    def test_own_public_reply_is_recorded_without_alert(self):
        base = {'ok': True, 'data': {'root_id': self.ids[0]},
                'messages': [{'id': self.ids[0], 'text': 'question'}]}
        a, _ = record(self.data, self.ids[0], base, '2026-10-24')
        later = copy.deepcopy(base)
        later['messages'].append({'id': self.ids[4], 'text': 'my reply',
                                  'author': PUTER_FINGERPRINT})
        b, receipt = record(a, self.ids[0], later, '2026-11-08')
        self.assertEqual(receipt['new_ids'], [])
        self.assertEqual(receipt['self_ids'], [self.ids[4]])
        self.assertIn(self.ids[4], b['threads'][0]['fingerprints'])

    def test_wrong_or_incomplete_page_never_persists(self):
        for meta in ({'root_id': 'other'}, {'root_id': self.ids[0], 'has_more': True}):
            with self.assertRaises(ValueError):
                record(self.data, self.ids[0], {'ok': True, 'data': meta,
                       'messages': [{'id': self.ids[0], 'text': 'sample'}]}, '2026-10-24')
        self.assertEqual(self.data['visits'], [])

    def test_atomic_save_load_and_no_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'queue.json'
            save(path, self.data)
            self.assertEqual(load(path), self.data)
            data = copy.deepcopy(self.data)
            data['threads'].append(data['threads'][0])
            save(path, data)
            with self.assertRaises(ValueError):
                load(path)

    def test_record_text_never_stored(self):
        body = 'public text not copied into record'
        raw = {'ok': True, 'data': {'root_id': self.ids[0]},
               'messages': [{'id': self.ids[0], 'text': body}]}
        new, _ = record(self.data, self.ids[0], raw, '2026-10-24')
        self.assertNotIn(body, json.dumps(new))


if __name__ == '__main__':
    unittest.main()
