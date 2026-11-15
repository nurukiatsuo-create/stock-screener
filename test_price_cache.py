import copy
import unittest
from price_cache import restore_confirmed_cache


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.row={'code':'1234','evidence':{'data_valid':True,'today':{'date':'2026-11-13'},'signal_date':'2026-11-13'},
                  'box_strategy':{'valid':True,'date':'2026-11-13'}}
        self.snapshot={'data_date':'2026-11-13','updated_at':'11/13 18:00','breakout_board':{'watching':[self.row]}}

    def test_same_date_reused_without_rewriting_origin(self):
        result,codes=restore_confirmed_cache({},self.snapshot,'2026-11-13')
        self.assertEqual(codes,['1234'])
        self.assertEqual(result['1234']['price_cached_updated_at'],'11/13 18:00')
        self.assertEqual(result['1234']['price_source'],'cached_confirmed')
        self.assertNotIn('price_source',self.row)

    def test_old_or_invalid_cache_cannot_hide_failure(self):
        self.assertEqual(restore_confirmed_cache({},self.snapshot,'2026-11-16')[1],[])
        self.row['box_strategy']['valid']=False
        self.assertEqual(restore_confirmed_cache({},self.snapshot,'2026-11-13')[1],[])

    def test_fresh_download_wins_and_conflicting_cache_is_rejected(self):
        row=copy.deepcopy(self.row);row['name']='fresh'
        result,codes=restore_confirmed_cache({'1234':row},self.snapshot,'2026-11-13')
        self.assertEqual(codes,[]);self.assertEqual(result['1234']['name'],'fresh')
        self.snapshot['breakout_board']['extra']=[row]
        self.assertEqual(restore_confirmed_cache({},self.snapshot,'2026-11-13')[1],[])


if __name__=='__main__':unittest.main()
