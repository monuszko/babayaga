#! /usr/bin/env python3

import string
import json
from itertools import groupby, product, zip_longest
from fractions import Fraction as Frac
from operator import itemgetter, attrgetter

MAGIC_PATHS = 'FAWESDNBH' # Sort order, etc

with open('gamedata.json', 'r') as datafile:
    data = json.load(datafile)

def sort_func(dic):
    combined = dic['path1']+dic['path2']
    return (len(combined), combined)

def spell_columns(spells, one_column=False, indent=4):
    indent = indent * ' '
    left, right = [], []
    spells = sorted(spells, key=sort_func, reverse=True)
    for sp in spells:
        if sp['mode'] in ('ritual', 'forge'):
            right.append(sp)
        else:
            left.append(sp)
    left = [' '.join([l['path1']+l['path2'], l['name']]).ljust(40) 
            for l in left]
    right = [' '.join([r['path1']+r['path2'], r['name']]).ljust(40) 
            for r in right]
    if one_column:
        output = indent + left + right
    else:
        output = zip_longest(left, right, fillvalue=' ' * 40)
        output = [indent + l + r for l, r in output]
    return output


class Mage:
    def __init__(self, paths, name, gcost=0):
        self.paths = paths
        self.name =  name 
        self.variants = []
        self.gcost = gcost

        self.generate_variants()
        self.reduce_variants()

    def __str__(self):
        return '{0} {1} ({2} gold)'.format(self.name, self.paths, self.gcost)

    def can_cast(self, variant, spell):
        if spell['path1'] in variant and spell['path2'] in variant:
            return True 
        return False 

    def only_castable(self, variant, spells):
        return [spell for spell in spells if self.can_cast(variant, spell)]

    def print_only_castable(self, variant, spells):
        castable = self.only_castable(variant[0], spells) 
        for line in spell_columns(castable):
            print(line)


    def spells_by_variant(self, spells, each_spell_once=True, ignored=set()):
        result = []
        dont_repeat = set() 
        for var in self.variants:
            paths = var[0]
            chance = var[1]
            castable = self.only_castable(paths, spells)
            if ignored:
                castable = [sp for sp in castable
                        if sp['hash'] not in ignored]
            if each_spell_once:
                castable = [sp for sp in castable 
                        if sp['hash'] not in dont_repeat]
                for sp in castable:
                    dont_repeat.add(sp['hash'])
            result.append(((paths, chance), castable))
        return result
    

    def print_spells_by_variant(self, spells, each_spell_once=True):
        by_variant = self.spells_by_variant(spells, each_spell_once)
        for var, sps in by_variant:
            if len(by_variant) > 1:
                print('Variant {0} ({1} chance)'.format(var[0], var[1]))
                print('-' * 25)
            for line in spell_columns(sps):
                print(line)


    def unpacked(self, token): 
        """ 100FEDN*2 """
        result = []
        parts = token.partition('*')
        bonus_size = parts[2] # Rare cases like King of the Deep
        bonus_size = 1 if not bonus_size else int(bonus_size)
        bonus_chance = Frac(int(parts[0].strip(string.ascii_letters)), 100)
        bonus_letters = parts[0].strip(string.digits)
        letter_chance = bonus_chance / len(bonus_letters)
        for letter in bonus_letters:
            result.append((letter * bonus_size, letter_chance))
        if bonus_chance < 1:
            result.append(('', 1 - bonus_chance))
        return result

    def generate_variants(self):
        tokens = self.paths.split(',') # 'FWWEEE,100FWE,10FWE' for Basalt King
        factors = [] # For cartesian product
        prefix = ('', Frac(1, 1))
        if tokens[0].isalpha():
            prefix = (tokens.pop(0), Frac(1, 1))
        factors.append([prefix])
        for token in tokens:
            factors.append(self.unpacked(token))
        while len(factors) > 1:
            first, second = factors.pop(0), factors.pop(0)
            product = [(f[0] + s[0], f[1] * s[1]) for f in first for s in second]
            product = [(''.join(sorted(paths, key=MAGIC_PATHS.index)), chance)
                                                  for paths, chance in product]
            factors.insert(0, product)
        self.variants = factors[0]

    def annotated_variants(self):
        pass

    def reduce_variants(self):
        newvars = sorted(self.variants)
        newvars = [(paths, sum(second for first, second in group)) 
                for paths, group in groupby(newvars, key=itemgetter(0))]
        newvars = [(paths, min(chance, Frac(1, 1))) for paths, chance in newvars]
        newvars = sorted(newvars, key=itemgetter(1), reverse=True)
        self.variants = newvars

    def possible_spells(self, spells):
        result = set()
        for spell in spells:
            for var in self.variants:
                if self.can_cast(var[0], spell):
                    result.add(spell['hash'])
                    break
        return result

class Nation:
    def __init__(self, ndata, mages):
        """ndata - nation's data from gamedata.json
           mages - all mages from gamedata.json"""
        self.name = ndata['name']
        self.epithet = ndata['epithet']
        self.nspells = ndata['nspells']

        for word in ('fort_mages', 'cap_mages', 'hero_mages', 'uw_mages'):
            x_mages = ndata[word]
            x_mages = [mages[xm] for xm in x_mages]
            x_mages = [Mage(xm['paths'], xm['name'], xm['gcost'])
                    for xm in x_mages]
            setattr(self, word, x_mages)


    def __str__(self):
        return '{0}: {1}'.format(self.name, self.epithet)


    def my_mages(self):
        mages = self.fort_mages + self.cap_mages + self.uw_mages
        mages = sorted(mages, key=attrgetter('gcost'))
        mages += self.hero_mages
        return mages 


    def recruitable_mages(self):
        mages = self.fort_mages + self.cap_mages + self.uw_mages
        mages = sorted(mages, key=attrgetter('gcost'))
        return mages 


    def first_in_second(self, first, second):
        if len(first.paths) > len(second.paths):
            return False
        if first.paths == second.paths: # correct, but pointless.
            return False
        tokens1 = first.paths.split(',')
        tokens2 = second.paths.split(',')
        prefix1 = tokens1.pop(0) if tokens1[0].isalpha() else ''
        prefix2 = tokens2.pop(0) if tokens2[0].isalpha() else ''
        groups1 = [''.join(list(b)) for a, b in groupby(prefix1)]
        for gr in groups1:
            if gr not in prefix2:
                return False
        for tk1 in tokens1:
            if tk1 not in tokens2:
                return False
            tokens2.remove(tk1) # FN,10FEDN,10FEDN would fit FN,10FEDN,10SWE !
        return True


    def print_spells_by_mage(self, spells):
        by_mage = self.spells_by_mage(spells)
        for mage, by_variant, includes in by_mage:
            print(mage)
            print('=' * 20)
            if includes:
                print(includes)
            for var, sps in by_variant:
                print('Variant {0} ({1} chance)'.format(var[0], var[1]))
                for line in spell_columns(sps):
                    print(line)


    def spells_by_mage(self, spells):
        result = [] # [(m, by_variant, includes), (...)]
        my_mages = self.my_mages()
        for m in my_mages:
            others =  [o for o in self.recruitable_mages()
                    if o.name != m.name and self.first_in_second(o, m)]
            includes = [o.name for o in others] # For message
            redundant = set()
            for o in others:
                redundant = redundant.union(o.possible_spells(spells))
            by_variant = m.spells_by_variant(spells, ignored=redundant)
            result.append((m, by_variant, includes))
        return result



mages = {int(k): v for k, v in data['mages'].items()} # no int keys in jascript
for ndata in data['nations']:
    nation = Nation(ndata, mages)
    print()
    print(nation)
    print('#' * 25)
    spells = data['spells'] + nation.nspells + data['items']

    nation.print_spells_by_mage(spells)

