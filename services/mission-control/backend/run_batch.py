#!/usr/bin/env python3
import requests, time
API = 'http://localhost:9999/api/submit_task'
tests = [
    ('Gio la may gio?',61), ('Hom nay ngay may?',62),
    ('Thoi tiet the nao?',63), ('Lap trinh la gi?',64),
    ('Hoc python o dau?',65), ('Khoa hoc online',66),
    ('Tai lieu hoc tap',67), ('Bai tap thuc hanh',68),
    ('Du an mau',69), ('ho tro ki thuat',70),
    ('Loi phan mem',71), ('Sua bug',72),
    ('Toi muon dong gop',73), ('Bao cao loi',74),
    ('Gop y',75), ('Phan hoi',76),
    ('Danh gia',77), ('Chat luong dich vu',78),
    ('Uu dai',79), ('Khuyen mai',80),
]
for g,i in tests:
    r = requests.post(API, json={'goal':g,'mode':'fast','source':'WEB'}, timeout=15)
    d = r.json()
    tid = d.get('task_id','')
    refl = d.get('is_social',False)
    print('Q{}: tid={} reflex={} ans_len={}'.format(i, tid, refl, len(d.get('answer',''))))
    time.sleep(0.3)
