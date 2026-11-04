import csv
import json
from pathlib import Path
import statistics
import unittest

ROOT=Path(__file__).resolve().parents[1]/'docs/benchmarks/2026-11-cheng'

class MetricTests(unittest.TestCase):
    def test_seed_scores_reproduce_confusion_matrices_means_and_csv(self):
        data=json.loads((ROOT/'metrics.json').read_text(encoding='utf-8'))
        with (ROOT/'seed_metrics.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
        for condition in ['without_skill','adaptive_with_skill']:
            for split in ['validation','test']:
                metrics=data[condition]['metrics'][split]
                for seed in metrics['seeds']:
                    cm=seed['confusion_matrix'];self.assertEqual(sum(map(sum,cm)),data['samples'][split])
                    f=[]
                    for i in range(3):
                        den=sum(cm[i])+sum(row[i] for row in cm);f.append(2*cm[i][i]/den if den else 0)
                    self.assertAlmostEqual(statistics.mean(f),seed['macro_f1'],places=12)
                    row=next(r for r in rows if r['condition']==condition and r['split']==split and int(r['seed'])==seed['seed'])
                    self.assertAlmostEqual(float(row['macro_f1']),seed['macro_f1'],places=12)
                scores=[r['macro_f1'] for r in metrics['seeds']]
                self.assertAlmostEqual(statistics.mean(scores),metrics['mean_macro_f1'],places=12)
                self.assertAlmostEqual(statistics.stdev(scores),metrics['sample_sd'],places=12)
        self.assertEqual(len(rows),12)
        self.assertGreaterEqual(data['adaptive_with_skill']['metrics']['validation']['mean_macro_f1'],data['adaptive_with_skill']['target'])
        lo,hi=data['patient_bootstrap']['interval'];self.assertLess(lo,0);self.assertGreater(hi,0)

if __name__=='__main__':unittest.main()
