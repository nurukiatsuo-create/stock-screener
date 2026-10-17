import unittest
import numpy as np
import pandas as pd
from box_strategy import analyze_boxes, detect_box, position_status, build_strategy
from breakout_evidence import analyze_breakout


def sample(n=65, base=100.):
    x = np.arange(n)
    close = base+4*np.sin(x*np.pi/5)
    return pd.DataFrame({'Open':close,'High':close+1,'Low':close-1,'Close':close,'Volume':1000.}, index=pd.bdate_range('2026-01-01',periods=n))


def append(df,o,h,l,c,v=2000):
    df=df.copy()
    df.loc[df.index[-1]+pd.offsets.BDay()] = [o,h,l,c,v]
    return df


class BoxTests(unittest.TestCase):
    def test_recognition_requires_reactions(self):
        self.assertIsNotNone(detect_box(sample()))
        d=sample();d[['Open','High','Low','Close']]=100
        self.assertIsNone(detect_box(d))
        d=sample();p=np.arange(len(d))*.1+100
        d['Open']=d['Close']=p;d['High']=p+1;d['Low']=p-1
        self.assertIsNone(detect_box(d))

    def test_fixed_boundary_and_intraday_rejection(self):
        d=sample(); before=analyze_boxes(d)['active_box']
        r=analyze_boxes(append(d,103,110,100,103))
        self.assertEqual(r['status'],'日中上抜け・終値未維持')
        self.assertEqual(r['active_box']['upper'],before['upper'])
        r=analyze_boxes(append(d,103,110,100,108))
        self.assertEqual(r['status'],'終値上抜け')

    def test_box_shift_and_no_lookahead(self):
        d=append(sample(),103,112,102,110)
        initial=analyze_boxes(d)
        new=sample(35,115);new.index=pd.bdate_range(d.index[-1]+pd.offsets.BDay(),periods=35)
        combined=pd.concat([d,new]);r=analyze_boxes(combined)
        self.assertEqual(r['status'],'新ボックス維持')
        self.assertGreater(r['active_box']['lower'],initial['active_box']['lower'])
        self.assertEqual(analyze_boxes(combined.iloc[:len(d)]) , initial)
        r=analyze_boxes(append(combined,115,116,105,106))
        self.assertEqual(r['status'],'下抜け確認')
        self.assertIsNone(r['active_box'])

    def test_missing_and_duplicates_fail_closed(self):
        d=sample();d.loc[d.index[1],'High']=np.nan
        self.assertFalse(analyze_boxes(d)['valid'])
        self.assertFalse(analyze_boxes(pd.concat([sample(),sample()]))['valid'])

    def test_exit_is_latched_and_stop_is_independent(self):
        d=sample();p=dict(buy_price=100,shares=100,buy_date=str(d.index[-1].date()),box_lower=94,box_upper=106)
        d=append(d,100,102,89,99)
        r=position_status(p,d,analyze_boxes(d))
        self.assertIn('10',r['status'])
        d=append(d,100,110,99,108)
        self.assertIsNotNone(position_status(p,d,analyze_boxes(d))['exit_event'])

    def test_no_fixed_profit_exit(self):
        d=sample();p=dict(buy_price=80,shares=100,buy_date=str(d.index[-1].date()),box_lower=94,box_upper=106)
        r=position_status(p,d,analyze_boxes(d))
        self.assertEqual(r['status'],'保有継続')
        self.assertGreater(r['pnl_pct'],20)

    def test_budget_is_not_recommendation_and_zero_candidates(self):
        d=sample(280);e=analyze_breakout(d,expected_date=str(d.index[-1].date()))
        obs={'1234':dict(name='test',evidence=e,box_strategy=analyze_boxes(d))}
        r=build_strategy(obs,{'budget_yen':1000000,'positions':[]})
        self.assertEqual(r['candidates'],[])
        self.assertLessEqual(r['observations'][0]['budget_preview']['cost'],1000000)
        self.assertEqual(r['observations'][0]['sector_check'],'未確認')

    def test_only_box_plus_new_high_is_candidate(self):
        d=append(sample(280),104,112,103,110)
        e=analyze_breakout(d,expected_date=str(d.index[-1].date()))
        obs={'1234':dict(name='test',evidence=e,box_strategy=analyze_boxes(d))}
        r=build_strategy(obs,{'positions':[]})
        self.assertEqual(len(r['candidates']),1)
        e['freshness']='日付不一致'
        self.assertEqual(build_strategy(obs,{'positions':[]})['candidates'],[])

    def test_later_high_after_box_break_and_return_inside(self):
        # Old 250-day high above a newer consolidation: two separate events.
        old=sample(200,120)
        recent=sample(80,100)
        recent.index=pd.bdate_range(old.index[-1]+pd.offsets.BDay(),periods=80)
        d=append(pd.concat([old,recent]),104,112,103,110)
        def result(frame):
            e=analyze_breakout(frame,expected_date=str(frame.index[-1].date()))
            b=analyze_boxes(frame)
            return build_strategy({'1234':dict(name='test',evidence=e,box_strategy=b)}, {})
        first=result(d)
        self.assertEqual(first['observations'][0]['status'],'ボックス突破・新高値未更新')
        self.assertEqual(first['candidates'],[])
        later=append(d,120,130,119,128)
        self.assertEqual(analyze_boxes(later)['status'],'上抜け後・新ボックス形成中')
        self.assertEqual(len(result(later)['candidates']),1)
        self.assertEqual(result(append(later,104,105,100,103))['candidates'],[])
        self.assertEqual(result(append(later,95,96,90,91))['candidates'],[])
        self.assertEqual(result(d),first)  # future bars cannot change the earlier decision

if __name__=='__main__': unittest.main()
