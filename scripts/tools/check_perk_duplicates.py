import json
import os
import sys


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def iter_heroes(dataset):
    heroes = dataset.get('heroes', [])
    if isinstance(heroes, dict):
        return heroes.items()

    result = []
    for hero in heroes:
        if not isinstance(hero, dict):
            continue
        hero_id = hero.get('id') or hero.get('name') or hero.get('Hero')
        result.append((hero_id, hero))
    return result


def normalized_content(perk):
    content = perk.get('content') or []
    lines = [str(line).strip() for line in content if str(line).strip()]
    return '\n'.join(lines).strip().lower()


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_path = os.path.join(base_dir, 'frontend', 'public', 'data', 'app_ready_dataset.json')
    if len(sys.argv) > 1:
        dataset_path = sys.argv[1]

    data = load_json(dataset_path)
    duplicated_heroes = []

    for hero_id, hero in iter_heroes(data):
        perks = hero.get('perks') or {}
        signatures = {}
        duplicated = False

        for group in ['minor', 'major']:
            for perk in perks.get(group, []) or []:
                sig = normalized_content(perk)
                perk_id = str(perk.get('id', ''))
                if not sig:
                    continue
                if sig in signatures and signatures[sig] != perk_id:
                    duplicated = True
                signatures[sig] = perk_id

        if duplicated:
            duplicated_heroes.append(hero_id)

    print(f'檢查檔案: {dataset_path}')
    print(f'同英雄內 perk 內容重複數量: {len(duplicated_heroes)}')
    if duplicated_heroes:
        print('重複英雄清單:')
        for hero_id in sorted(duplicated_heroes):
            print(f' - {hero_id}')
        sys.exit(1)

    print('✅ 未發現同英雄內 perk 內容重複')


if __name__ == '__main__':
    main()
