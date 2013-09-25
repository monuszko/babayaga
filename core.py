#! /usr/bin/env python3
#
# Baba Yaga - lists spells castable by mages in computer games 'Dominions 3'
# and 'Dominions 4'.
#
#    Copyright (C) 2013  Marek Onuszko
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import string
import json
from itertools import groupby, product, zip_longest
from fractions import Fraction as Frac
from operator import itemgetter, attrgetter

MAGIC_PATHS = 'FAWESDNBH' # Sort order, etc

with open('gamedata.json', 'r') as datafile:
    data = json.load(datafile)

def human(paths):
    if not paths.startswith(tuple(MAGIC_PATHS)):
        fixed = ''
    else:
        fixed = paths.split(',')[0]
    humanized = ''.join([a + str(len(list(b))) for a, b in groupby(fixed)])
    return paths.replace(fixed, humanized)

def sort_func(dic):
    combined = dic['path1']+dic['path2']
    return (len(combined), combined)

def spell_columns(spells):
    """Returns spells divided into two columns:
    - battle spells
    - rituals&forgings"""
    left, right = [], []
    for sp in spells:
        if sp['mode'] in ('ritual', 'forge'):
            right.append(sp)
        else:
            left.append(sp)
    return (left, right)

def reST_words(spells):
    """[{spell:1}, {spell:2}] ---> [['paths1', 'name1'], ['paths2', 'name2']]
    """
    spells = [(sp['path1']+sp['path2'], sp['gems'], 
               sp['name'].replace("'", "\\\'"),
               sp['level'], sp['boosts']) for sp in spells]
    max_widths = [max([len(word) for word in col]) for col in zip(*spells)]
    max_widths = [max(2, width) for width in max_widths]
    spells = [[word.ljust(max_widths[nr]) for nr, word in enumerate(row)]
                 for row in spells]
    return spells


class Mage:
    def __init__(self, paths, name, gcost=0):
        self.paths = paths
        self.name =  name 
        self.variants = []
        self.gcost = gcost

        self.generate_variants()

    def __str__(self):
        return '{0} {1} ({2} gold)'.format(self.name, 
                human(self.paths), self.gcost)

    def can_cast(self, variant, spell):
        for path in (spell['path1'], spell['path2']):
            if path not in variant['paths']:
                return False
        return True

    def chance_to_cast(self, spell):
        chance = 0
        for v in self.get_variants(add_prefix=False):
            if self.can_cast(v, spell):
                chance += v['chance']
        return chance

    def only_castable(self, variant, spells):
        spells = [spell for spell in spells if self.can_cast(variant, spell)]
        return sorted(spells, key=sort_func, reverse=True)

    def print_only_castable(self, variant, spells):
        castable = self.only_castable(variant[0], spells) 
        for line in spell_columns(castable):
            print(line)


    def spells_by_variant(self, spells, each_spell_once=True, ignored=set()):
        result = []
        dont_repeat = set() 
        for var in self.get_variants():
            chance = var['chance']
            castable = self.only_castable(var, spells)
            if ignored:
                castable = [sp for sp in castable
                        if sp['hash'] not in ignored]
            if each_spell_once:
                castable = [sp for sp in castable 
                        if sp['hash'] not in dont_repeat]
                for sp in castable:
                    dont_repeat.add(sp['hash'])
            result.append((var, castable))
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
        self.prefix = {'paths': prefix[0], 'chance': prefix[1], 'meta': ''}
        for token in tokens:
            factors.append(self.unpacked(token))
        while len(factors) > 1:
            first, second = factors.pop(0), factors.pop(0)
            product = [(f[0] + s[0], f[1] * s[1]) for f in first for s in second]
            product = [(''.join(sorted(paths, key=MAGIC_PATHS.index)), chance)
                                                  for paths, chance in product]
            factors.insert(0, product)
        self.variants = [{'paths': f[0], 'chance': f[1], 'meta': ''}
                for f in factors[0]]
        self.reduce_variants()
        self.annotate_variants()

    def annotate_variants(self):
        prefix_in_variants = False
        for var in self.variants:
            if len(self.variants) == 1:
                var['meta'] = '(The sole variant)'
                prefix_in_variants = True
            elif var['paths'] == self.prefix['paths'] and var['paths']:
                var['meta'] = '({} chance) (Common to all)'.format(var['chance'])
                prefix_in_variants = True
            else:
                var['meta'] = '({} chance)'.format(var['chance'])
        if not prefix_in_variants:
            self.prefix['meta'] = "(Doesn't occur) (Common to all)"

    def reduce_variants(self):
        tmp = dict()
        for v in self.variants:
            paths = v['paths']
            if paths not in tmp:
                tmp[paths] = v
            else:
                tmp[paths]['chance'] += v['chance']

        self.variants = [v for v in tmp.values()]
        self.variants.sort(key=itemgetter('chance'), reverse=True)

        # Sanity check:
        total = sum(v['chance'] for v in self.variants)
        assert total == 1

    def get_variants(self, add_prefix=True):
        if 'sole variant' not in self.prefix['meta'] or not add_prefix:
            return self.variants
        return [self.prefix].extend(self.variants)

    def possible_spells(self, spells):
        result = set()
        for spell in spells:
            for var in self.variants:
                if self.can_cast(var, spell):
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

        self.nsmages = []
        for spell in self.nspells:
            if spell['sumages']:
                self.nsmages.extend(spell['sumages'])
        self.nsmages = [mages[ns] for ns in self.nsmages]

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


    def first_in_second2(self, first, second, spells):
        for spell in spells:
            if first.chance_to_cast(spell) > second.chance_to_cast(spell):
                return False
        return True

    def print_spells_by_mage(self, spells, two_columns=True, fmt='reST'):
        by_mage = self.spells_by_mage(spells)
        for mage, by_variant, includes in by_mage:
            m = str(mage)
            print(m)
            print('=' * len(m))
            if includes:
                includes = ', '.join(includes)
                includes = ' and'.join(includes.rsplit(',', 1))
                print('Omitting spells from {0}.'.format(includes))
            print()
            for var, sps in by_variant:
                print('Variant {0} {1}:'.format(human(var['paths']), var['meta']))
                if not sps:
                    print()
                    continue
                col1, col2 = spell_columns(sps)
                col1 = reST_words(col1)
                col2 = reST_words(col2)
                if len(col1) > len(col2):
                    words = col2[0] if col2 else col1[0]
                    fill = ['\\'.ljust(len(word)) for word in words]
                else:
                    words = col1[0] if col1 else col2[0]
                    fill = ['\\'.ljust(len(word)) for word in words]
                lines = zip_longest(col1, col2, fillvalue = fill)
                lines = [left + right for left, right in lines]
                border = ['=' * len(word) for word in lines[0]]
                lines.insert(0, border)
                lines.append(border)
                lines = [' '.join(line) for line in lines]
                for line in lines:
                    print(' '*2 + line)
                print()


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
print('.. contents::')
print()
for ndata in data['nations']:
    nation = Nation(ndata, mages)
    nat = str(nation)
    print(nat)
    print('#' * len(nat))
    if nation.nsmages:
        print('NSMAGES!')
    for nsmage in nation.nsmages:
        print(nsmage['name'], nsmage['paths'])
    spells = data['spells'] + nation.nspells + data['items']

    nation.print_spells_by_mage(spells)

