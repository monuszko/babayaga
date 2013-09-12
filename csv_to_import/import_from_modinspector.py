#! /usr/bin/env python3



# TODO: Nyan Cat pretender mod

import csv
import json
MAGIC_PATHS = 'FAWESDNBH' # Sort order, etc

path_legend = {0: 'F',
               1: 'A',
               2: 'W',
               3: 'E',
               4: 'S',
               5: 'D',
               6: 'N',
               7: 'B',
               8: 'H',
        }


def unmasked(mask):
    result = ''
    legend = {128: 'F', 
              256: 'A',
              512: 'W', 
              1024: 'E',
              2048: 'S',
              4096: 'D',
              8192: 'N',
              16384: 'B',
              32768: 'H'}
    for k in sorted(legend):
        if mask & k:
            result += legend[k]
    return result

def read_sites(filename):
    """ Only used to get capitol only mages """
    with open(filename, 'r') as sitefile:
        reader = csv.DictReader(sitefile, delimiter='\t')
        rows = [row for row in reader]
        sites = dict()
        for row in rows:
            for k, v in row.items():
                row[k] = int(v) if v.isdigit() else v
            site_id = row['id']
            gem_inc = ''
            for path in MAGIC_PATHS.strip('H'):
                if row[path]:
                    gem_inc += path.lower() * row[path]
            comms = []
            for n in range(1, 5):
                comms.append(row['com' + str(n)])
                comms.append(row['hcom' + str(n)])
            comms = [comm for comm in comms if comm]
            sites[site_id] = {'gem_inc': gem_inc, 'comms': comms}
    return sites


def read_mages(filename):
    with open(filename, 'r') as unitfile:
        reader = csv.DictReader(unitfile, delimiter='\t')
        rows = [row for row in reader]
        mages = dict()
        for row in rows:
            for k, v in row.items():
                row[k] = int(v) if v.isdigit() else v
            unit_id = row['id']
            name = row['name'] if not row['uniquename'] else row['uniquename']
            paths = ''
            gcost = row['gcost']
            # TODO: Gift of Reason + Asrapa (hidden magic paths)
            for path in MAGIC_PATHS:
                if row[path]:
                    paths += row[path] * path
            for n in '1234':
                if row['rand' + n]:
                    chance = str(row['rand' + n])
                    repeats = row['nbr' + n] # A mage with two 50% FW randoms has 2
                    bonus_size = ''
                    if row['link' + n] and row['link' + n] > 1: # Warlock fix
                        bonus_size = '*' + str(row['link' + n])
                    choice = unmasked(row['mask' + n])
                    token = chance + choice + bonus_size
                    paths += (',' + token) * repeats
            paths = paths.lstrip(',') # Mages without base paths
            if not paths:
                continue # This project explores capabilities of mages ONLY.
            mages[unit_id] = {'name': name, 'paths': paths, 'gcost': gcost}
    return mages 


def read_nations(filename, mages, sites):
    """ mages needed to filter spellcasting commanders """
    with open(filename, 'r') as nationfile:
        reader = csv.DictReader(nationfile, delimiter='\t')
        rows = [row for row in reader]
        nations = dict()
        for row in rows:
            for k, v in row.items():
                row[k] = int(v) if v.isdigit() else v
            nation_id = row['id']
            name = row['name']
            epithet = row['epithet']
            era = row['era']

            comm_fields = ['com' + str(n) for n in range(1, 13)]
            fort_mages = [row[comm] for comm in comm_fields]
            fort_mages = [m for m in fort_mages if m in mages]

            hero_fields = ['hero' + str(n) for n in range(1, 7)]
            hero_mages = [row[hero] for hero in hero_fields]
            hero_mages = [h for h in hero_mages if h in mages]

            uw_fields = ['uwc' + str(n) for n in range(1, 6)]
            uw_mages = [row[uwc] for uwc in uw_fields]
            uw_mages = [uw for uw in uw_mages if uw in mages]

            gem_inc = ''
            cap_mages = []
            cap_sites = [row['site' + str(n)] for n in range(1, 5)]
            cap_sites = [sites[c] for c in cap_sites if c]
            for s in cap_sites:
                cap_mages.extend(s['comms'])
                gem_inc += s['gem_inc']
            cap_mages = [comm for comm in cap_mages if comm in mages]
            gem_inc = ''.join(sorted(gem_inc))

            nations[nation_id] = {'name': name, 'epithet': epithet, 'era': era,
                    'fort_mages': fort_mages, 'hero_mages': hero_mages,
                    'cap_mages': cap_mages, 'uw_mages': uw_mages,
                    'gem_inc': gem_inc}
    return nations

def read_spells(filename, mages):
    """ Mages argument used to mark spells summoning mages """
    with open('Spells.csv', 'r') as spellfile:
        reader = csv.DictReader(spellfile, delimiter='\t')
        rows = [row for row in reader if row['school'] != '255']
        spells = []
        for row in rows:
            for k, v in row.items():
                row[k] = int(v) if v.isdigit() else v
            name = row['name']
            path1 = path_legend[row['path1']] * row['pathlevel1']
            path2 = '' if row['path2'] == 255 else path_legend[row['path2']]
            nation_fields = ['restricted' + str(n) for n in range(1, 8)]
            nations = [row[nation] for nation in nation_fields if row[nation]]
            # Summoned normal, unique commander mages  expand magic versatility:
            mage = None
            if row['effect'] in (10021, 10089, 10093):
                mage = row['damage']
            mode = 'combat' if row['effect'] < 10000 else 'ritual'
            mage = mage if mage in mages else None
            hash_id = 's' + str(row['id'])
            spells.append({'name': name, 'path1': path1, 'path2': path2,
                'nations': nations, 'mage': mage, 'mode': mode, 'hash': hash_id})
    return spells

def read_items(filename):
    with open('BaseI.csv', 'r') as itemfile:
        reader = csv.DictReader(itemfile, delimiter='\t')
        rows = [row for row in reader if row['constlevel'] != '12']
        magic_items = []
        for row in rows:
            for k, v in row.items():
                row[k] = int(v) if v.isdigit() else v
            name = row['name']
            level = row['constlevel']
            path1 = row['mainpath'] * row['mainlevel']
            path2 = ''
            hash_id = 'i' + str(row['id'])
            if row['secondarypath']:
                path2 = row['secondarypath'] * row['secondarylevel']
            boosts = ''
            for path in MAGIC_PATHS:
                if row[path]:
                    boosts += path * row[path]
            magic_items.append({'name': name, 'level': level, 'path1': path1,
                'path2': path2, 'boosts': boosts, 'mode': 'forge',
                'hash': hash_id})

    return magic_items


def prepare_output(nations, spells, mages, magic_items):
    output = dict()
    output['mages'] = mages
    output['nations'] = []
    for nat_id, nat in nations.items():
        if nat_id in (6, 23, 24, 25):
            continue # (reserved), Independents, Special Monsters x2
        nat['nspells'] = [sp.copy() for sp in spells if nat_id in sp['nations']]
        for nspell in nat['nspells']:
            del nspell['nations'] # This is why I'm using .copy() above.
        output['nations'].append(nat)

    output['spells'] = [spell for spell in spells if not spell['nations']]
    for spell in output['spells']:
        del spell['nations']
    output['items'] = magic_items
    return output

sites = read_sites('MagicSites.csv')
mages = read_mages('BaseU.csv')
nations = read_nations('Nations.csv', mages, sites)
spells = read_spells('Spells.csv', mages)
magic_items = read_items('BaseU.csv')
output = prepare_output(nations, spells, mages, magic_items)

with open('../gamedata.json', 'w') as outfile:
    json.dump(output, outfile, sort_keys=True, indent=4)



