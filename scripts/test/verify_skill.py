import importlib.util
spec = importlib.util.spec_from_file_location('test', '/intelligence/skills/skill_giam_sat_he_thong/logic.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print('HAS bao_cao_suc_khoe_he_thong:', hasattr(m, 'bao_cao_suc_khoe_he_thong'))
print('HAS quet_loi:', hasattr(m, 'quet_loi_log_tu_dong'))
print('Module attrs:', [a for a in dir(m) if not a.startswith('_')])
