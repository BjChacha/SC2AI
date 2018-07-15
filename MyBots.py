import random
import time
import os
import cv2
import numpy as np
from sc2 import BotAI, Result, position
from sc2.constants import (ASSIMILATOR, CYBERNETICSCORE, GATEWAY, IMMORTAL,
                           NEXUS, OBSERVER, PROBE, PYLON, ROBOTICSFACILITY,
                           STALKER, STARGATE, VOIDRAY)


# 165 iteration per minute
class MyBot(BotAI):
    def __init__(self):
        self.ITERATIONS_PER_MINUTE = 165
        self.MAX_WORKERS = 60
        self.SUPPLY_OFFSET_DIV_FACTOR = 4
        self.SUPPLY_OFFSET_ADD_FACTOR = 5
        self.MAX_SUPPLY = 200
        self.MAX_NEXUS = 4
        self.MAX_ASSIMILATORS = 4
        self.MAX_FIRST_FACTORY = 2
        self.MAX_SECOND_FACTORY = 3
        self.EXPAND_TIMEGAP = 0
        self.FIRST_ATTACK_UNIT = None
        self.SECOND_ATTACK_UNIT = None
        self.FIRST_FACTORY = None
        self.SECOND_FACTORY = None

    async def on_step(self, iteration):
        self.iteration = iteration
        # print("{0:.2f}".format(self.iteration / self.ITERATIONS_PER_MINUTE))
        await self.distribute_workers()
        await self.scout()
        await self.build_workers(max_amount=self.MAX_WORKERS)
        await self.build_pylons(iteration / self.ITERATIONS_PER_MINUTE // self.SUPPLY_OFFSET_DIV_FACTOR + self.SUPPLY_OFFSET_ADD_FACTOR)
        await self.build_assimilators(max_amount=self.MAX_ASSIMILATORS)
        await self.expand(max_amount=self.MAX_NEXUS, expand_timegap=self.EXPAND_TIMEGAP)
        await self.offensive_force_building(max_amount_of_first_factory=self.MAX_FIRST_FACTORY, max_amount_of_second_factory=self.MAX_SECOND_FACTORY)
        await self.train_offensive_force()
        await self.attack(defend_amount=5, attack_amount=28)

    async def scout(self):
        if len(self.units(OBSERVER)) > 0:
            scout = self.units(OBSERVER)[0]
            if scout.is_idle:
                enemy_location = self.enemy_start_locations[0]
                move_to = self.random_location_variance(enemy_location)
                print("Scout!")
                await self.do(scout.move(move_to))
        else:
            for rf in self.units(ROBOTICSFACILITY).ready.noqueue:
                if self.can_afford(OBSERVER) and self.supply_left > 1:
                    await self.do(rf.train(OBSERVER))

    def random_location_variance(self,enemy_start_location):
        x = enemy_start_location[0]
        y = enemy_start_location[1]
        x *= ((random.randrange(-20, 20))/100) + 1
        y *= ((random.randrange(-20, 20))/100) + 1
        x = 0 if x < 0 else x
        x = self.game_info.map_size[0] if x > self.game_info.map_size[0] else x
        y = 0 if y < 0 else y
        y = self.game_info.map_size[1] if y > self.game_info.map_size[1] else y

        go_to = position.Point2(position.Pointlike((x, y)))
        return go_to


    async def build_workers(self, max_amount):
        for nexus in self.units(NEXUS).ready.noqueue:
            if self.can_afford(PROBE) and self.units(PROBE).amount <= self.units(NEXUS).amount * 16 and self.units(PROBE).amount < max_amount:
                await self.do(nexus.train(PROBE))

    async def build_pylons(self, supply_offset=5):
        if self.supply_cap < self.MAX_SUPPLY and self.supply_left <= supply_offset and not self.already_pending(PYLON):
            nexuses = self.units(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(PYLON, near=nexuses.first)

    async def build_assimilators(self, max_amount, amount_per_nexus=2):
        for nexus in self.units(NEXUS).ready:
            if self.units(PYLON).ready and self.units(self.FIRST_FACTORY).ready:
                if self.can_afford(ASSIMILATOR) and self.units(ASSIMILATOR).amount < max_amount and self.units(ASSIMILATOR).amount < self.units(NEXUS).amount * amount_per_nexus:
                    vespenes = self.state.vespene_geyser.closer_than(15.0, nexus)
                    for vespene in vespenes:
                        worker = self.select_build_worker(vespene.position)
                        if worker and not self.units(ASSIMILATOR).closer_than(1.0, vespene).exists:
                            await self.do(worker.build(ASSIMILATOR, vespene))
                            break

    async def expand(self, max_amount, expand_timegap):
        if self.units(NEXUS).amount < max_amount and self.can_afford(NEXUS) and self.units(NEXUS).amount < (self.iteration / self.ITERATIONS_PER_MINUTE) // expand_timegap + 1:
            await self.expand_now()

    async def offensive_force_building(self, max_amount_of_first_factory, max_amount_of_second_factory):
        if self.units(PYLON).ready.exists:
            # Build Cybernetics Core
            if self.units(self.FIRST_FACTORY).ready.exists and not (self.units(CYBERNETICSCORE).exists or self.already_pending(CYBERNETICSCORE)):
                if self.can_afford(CYBERNETICSCORE):
                    pylon = self.units(PYLON).ready.random
                    await self.build(CYBERNETICSCORE, near=pylon)
            # Build Gate Way
            elif self.units(self.FIRST_FACTORY).amount < self.units(NEXUS).ready.amount * 2 and self.units(self.FIRST_FACTORY).amount < max_amount_of_first_factory:
                if self.can_afford(self.FIRST_FACTORY):
                    pylon = self.units(PYLON).ready.random
                    await self.build(self.FIRST_FACTORY, near=pylon)
            # Build Robotics Facility
            elif self.units(CYBERNETICSCORE).ready.exists :
                if not (self.SECOND_FACTORY == ROBOTICSFACILITY or self.units(ROBOTICSFACILITY).exists):
                    if self.can_afford(ROBOTICSFACILITY) and not (self.already_pending(ROBOTICSFACILITY) or self.units(ROBOTICSFACILITY).exists) :
                            pylon = self.units(PYLON).ready.random
                            await self.build(ROBOTICSFACILITY, near=pylon)
            # Build Star Gate
                else:
                    if self.iteration / self.ITERATIONS_PER_MINUTE > 2 and self.units(self.SECOND_FACTORY).amount < max_amount_of_second_factory:
                        if self.can_afford(self.SECOND_FACTORY) and not self.already_pending(self.SECOND_FACTORY):
                            pylon = self.units(PYLON).ready.random
                            await self.build(self.SECOND_FACTORY, near=pylon)

    async def train_offensive_force(self):
        if self.units(CYBERNETICSCORE).ready:
            for sg in self.units(self.SECOND_FACTORY).ready.noqueue:
                if self.can_afford(self.SECOND_ATTACK_UNIT) and self.supply_left > 3 :
                    await self.do(sg.train(self.SECOND_ATTACK_UNIT))
            for gw in self.units(self.FIRST_FACTORY).ready.noqueue:
                if self.can_afford(self.FIRST_ATTACK_UNIT) and self.supply_left > 1 and (self.units(self.FIRST_ATTACK_UNIT).amount < 21 or self.units(self.FIRST_ATTACK_UNIT).amount < self.units(self.SECOND_ATTACK_UNIT).amount * 3):
                    await self.do(gw.train(self.FIRST_ATTACK_UNIT))

    async def attack(self, defend_amount, attack_amount):
        if self.units(self.FIRST_ATTACK_UNIT).amount + self.units(self.SECOND_ATTACK_UNIT).amount >= attack_amount:
            print("Attack!")
            for s in self.units(self.FIRST_ATTACK_UNIT).idle:
                if self.known_enemy_structures:
                    await self.do(s.attack(random.choice(self.known_enemy_structures)))
                else:
                    await self.do(s.attack(self.enemy_start_locations[0]))
            for v in self.units(self.SECOND_ATTACK_UNIT).idle:
                if self.known_enemy_structures:
                    await self.do(v.attack(random.choice(self.known_enemy_structures)))
                else:
                    await self.do(v.attack(self.enemy_start_locations[0]))
        elif self.units(self.FIRST_ATTACK_UNIT).amount + self .units(self.SECOND_ATTACK_UNIT).amount >= defend_amount:
            if self.known_enemy_units.exists:
                for enemy in self.known_enemy_units.not_structure: 
                    # print(enemy.position.to2.distance_to(self.start_location.to2))
                    if enemy.position.to2.distance_to(self.start_location.to2) < 15 * self.units(NEXUS).amount + 5:
                        print("Defend!")
                        for s in self.units(self.FIRST_ATTACK_UNIT).idle:
                            await self.do(s.attack(enemy))
                        for v in self.units(self.SECOND_ATTACK_UNIT).idle:
                            await self.do(v.attack(enemy))
                        break


class ChaBot1(MyBot):
    def __init__(self):
        super().__init__()
        self.SUPPLY_OFFSET_DIV_FACTOR = 3
        self.SUPPLY_OFFSET_ADD_FACTOR = 5
        self.MAX_NEXUS = 4
        self.MAX_ASSIMILATORS = 4
        self.MAX_FIRST_FACTORY = 2
        self.MAX_SECOND_FACTORY = 3
        self.EXPAND_TIMEGAP = 2
        self.FIRST_ATTACK_UNIT = STALKER
        self.SECOND_ATTACK_UNIT = VOIDRAY
        self.FIRST_FACTORY = GATEWAY
        self.SECOND_FACTORY = STARGATE


class ChaBot2(MyBot):
    def __init__(self):
        super().__init__()
        self.SUPPLY_OFFSET_DIV_FACTOR = 4
        self.SUPPLY_OFFSET_ADD_FACTOR = 5
        self.MAX_NEXUS = 2
        self.MAX_ASSIMILATORS = 2
        self.MAX_FIRST_FACTORY = 2
        self.MAX_SECOND_FACTORY = 2
        self.EXPAND_TIMEGAP = 1.5
        self.FIRST_ATTACK_UNIT = STALKER
        self.SECOND_ATTACK_UNIT = IMMORTAL
        self.FIRST_FACTORY = GATEWAY
        self.SECOND_FACTORY = ROBOTICSFACILITY


class ChaBotDL(ChaBot1):
    def __init__(self):
        super().__init__()
        self.MAX_WORKERS = 50
        self.do_something_ater = 0
        self.train_data = []
        self.MAX_ASSIMILATORS = 6
        self.MAX_NEXUS = 5
        self.BASIC_REACTION = 5
    
    def on_end(self, game_result):
        print('--- on_end called ---')
        print(game_result)

        if game_result == Result.Victory:
            save_path = (os.getcwd() + '/train_data/')
            if not os.path.exists(save_path): os.makedirs(save_path)
            np.save(save_path + "{}.npy".format(str(int(time.time()))), np.array(self.train_data))

    async def on_step(self, iteration):
        await super().on_step(iteration)
        await self.visualize()

    async def visualize(self):
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)

        draw_dict = {
            NEXUS: [15, (0, 255, 0)],
            PYLON: [3, (20, 235, 0)],
            PROBE: [1, (55, 200, 0)],

            ASSIMILATOR: [2, (55, 200, 0)],
            GATEWAY: [3, (200, 100, 0)],
            CYBERNETICSCORE: [3, (150, 150, 0)],
            STARGATE: [5, (255, 0, 0)],
            ROBOTICSFACILITY: [5, (215, 155, 0)],
            STALKER: [3, (135, 135, 50)],
            VOIDRAY: [3, (255, 100, 0)],
            }
        for unit_type in draw_dict:
            for unit in self.units(unit_type).ready:
                pos = unit.position
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dict[unit_type][0], draw_dict[unit_type][1], -1)

        main_base_name = ['nexus', 'supplydepot', 'hatchery']
        worker_names = ["probe", "scv", "drone"]
        for enemy_building in self.known_enemy_structures:
            pos = enemy_building.position
            if enemy_building.name.lower() not in main_base_name:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 5, (200, 50, 212), -1)
            else:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 15, (0, 0, 255), -1)

        for enemy_unit in self.known_enemy_units.not_structure:
            pos = enemy_unit.position
            if enemy_unit.name.lower() in worker_names:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (55, 0, 155), -1)
            else:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (50, 0, 215), -1)

        for obs in self.units(OBSERVER).ready:
            pos = obs.position
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (255, 255, 255), -1)

        line_max = 50
        mineral_ratio = self.minerals / 1500
        if mineral_ratio > 1:
            mineral_ratio = 1
        vespene_ratio = self.vespene / 1500
        if vespene_ratio > 1:
            vespene_ratio = 1
        population_ratio = self.supply_left / self.supply_cap
        if population_ratio > 1:
            population_ratio = 1
        plausible_supply = self.supply_cap / 200.0

        military_weight = (len(self.units(self.FIRST_ATTACK_UNIT)) + len(self.units(self.SECOND_ATTACK_UNIT))) \
                            / (self.supply_cap - self.supply_left)
        if military_weight > 1:
            military_weight = 1

        cv2.line(game_data, (0, 19), (int(line_max * military_weight), 19), (255, 250, 200), 3)
        cv2.line(game_data, (0, 15), (int(line_max * plausible_supply), 15), (220, 200, 200), 3)
        cv2.line(game_data, (0, 11), (int(line_max * population_ratio), 11), (150, 150, 150), 3)
        cv2.line(game_data, (0, 7), (int(line_max * vespene_ratio), 7), (210, 200, 0), 3)
        cv2.line(game_data, (0, 3), (int(line_max * mineral_ratio), 3), (0, 255, 25), 3)

        self.flipped = cv2.flip(game_data, 0)
        resized = cv2.resize(self.flipped, dsize=None, fx=2, fy=2)
        cv2.imshow("SC2AI", resized)
        cv2.waitKey(1)


    async def attack(self, **karg):
        if self.units(VOIDRAY).amount + self.units(STALKER).amount > 0:
            choice = random.randrange(0, 4)
            target = None
            if self.iteration > self.do_something_ater:
                if choice == 0:
                    print("Wait!")
                    wait = random.randrange(self.BASIC_REACTION, 165)
                    self.do_something_ater = self.iteration + wait
                elif choice == 1:
                    print("Defend!")
                    if self.known_enemy_units.amount > 0:
                        target = self.known_enemy_units.closest_to(random.choice(self.units(NEXUS)))
                    self.do_something_ater = self.iteration + self.BASIC_REACTION
                elif choice == 2:
                    print("Attack!")
                    if self.known_enemy_structures.amount > 0:
                        target = random.choice(self.known_enemy_structures)
                    self.do_something_ater = self.iteration + self.BASIC_REACTION
                elif choice == 3:
                    print("Finally Attack!")
                    target = self.enemy_start_locations[0]
                    self.do_something_ater = self.iteration + self.BASIC_REACTION

                if target:
                    for vr in self.units(VOIDRAY).idle:
                        await self.do(vr.attack(target))
                    for sk in self.units(STALKER).idle:
                        await self.do(sk.attack(target))

                y = np.zeros(4)
                y[choice] = 1
                # print(y)
                self.train_data.append([y, self.flipped])


class SentdeBot(BotAI):
    def __init__(self):
        self.ITERATIONS_PER_MINUTE = 165
        self.MAX_WORKERS = 50
        self.do_something_after = 0
        self.train_data = []

    def on_end(self, game_result):
        print('--- on_end called ---')
        print(game_result)

        if game_result == Result.Victory:
            np.save("train_data_{}.npy".format(str(int(time.time()))), np.array(self.train_data))

    async def on_step(self, iteration):
        self.iteration = iteration
        await self.scout()
        await self.distribute_workers()
        await self.build_workers()
        await self.build_pylons()
        await self.build_assimilators()
        await self.expand()
        await self.offensive_force_buildings()
        await self.build_offensive_force()
        await self.intel()
        await self.attack()

    def random_location_variance(self, enemy_start_location):
        x = enemy_start_location[0]
        y = enemy_start_location[1]

        x += ((random.randrange(-20, 20))/100) * enemy_start_location[0]
        y += ((random.randrange(-20, 20))/100) * enemy_start_location[1]

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x > self.game_info.map_size[0]:
            x = self.game_info.map_size[0]
        if y > self.game_info.map_size[1]:
            y = self.game_info.map_size[1]

        go_to = position.Point2(position.Pointlike((x,y)))
        return go_to

    async def scout(self):
        if len(self.units(OBSERVER)) > 0:
            scout = self.units(OBSERVER)[0]
            if scout.is_idle:
                enemy_location = self.enemy_start_locations[0]
                move_to = self.random_location_variance(enemy_location)
                print(move_to)
                await self.do(scout.move(move_to))

        else:
            for rf in self.units(ROBOTICSFACILITY).ready.noqueue:
                if self.can_afford(OBSERVER) and self.supply_left > 0:
                    await self.do(rf.train(OBSERVER))

    async def intel(self):
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)

        # UNIT: [SIZE, (BGR COLOR)]
        '''from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, \
 CYBERNETICSCORE, STARGATE, VOIDRAY'''
        draw_dict = {
                     NEXUS: [15, (0, 255, 0)],
                     PYLON: [3, (20, 235, 0)],
                     PROBE: [1, (55, 200, 0)],
                     ASSIMILATOR: [2, (55, 200, 0)],
                     GATEWAY: [3, (200, 100, 0)],
                     CYBERNETICSCORE: [3, (150, 150, 0)],
                     STARGATE: [5, (255, 0, 0)],
                     ROBOTICSFACILITY: [5, (215, 155, 0)],

                     VOIDRAY: [3, (255, 100, 0)],
                     #OBSERVER: [3, (255, 255, 255)],
                    }

        for unit_type in draw_dict:
            for unit in self.units(unit_type).ready:
                pos = unit.position
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dict[unit_type][0], draw_dict[unit_type][1], -1)

        main_base_names = ["nexus", "supplydepot", "hatchery"]
        for enemy_building in self.known_enemy_structures:
            pos = enemy_building.position
            if enemy_building.name.lower() not in main_base_names:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 5, (200, 50, 212), -1)
        for enemy_building in self.known_enemy_structures:
            pos = enemy_building.position
            if enemy_building.name.lower() in main_base_names:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 15, (0, 0, 255), -1)

        for enemy_unit in self.known_enemy_units:

            if not enemy_unit.is_structure:
                worker_names = ["probe",
                                "scv",
                                "drone"]
                # if that unit is a PROBE, SCV, or DRONE... it's a worker
                pos = enemy_unit.position
                if enemy_unit.name.lower() in worker_names:
                    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (55, 0, 155), -1)
                else:
                    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (50, 0, 215), -1)

        for obs in self.units(OBSERVER).ready:
            pos = obs.position
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (255, 255, 255), -1)

        line_max = 50
        mineral_ratio = self.minerals / 1500
        if mineral_ratio > 1.0:
            mineral_ratio = 1.0

        vespene_ratio = self.vespene / 1500
        if vespene_ratio > 1.0:
            vespene_ratio = 1.0

        population_ratio = self.supply_left / self.supply_cap
        if population_ratio > 1.0:
            population_ratio = 1.0

        plausible_supply = self.supply_cap / 200.0

        military_weight = len(self.units(VOIDRAY)) / (self.supply_cap-self.supply_left)
        if military_weight > 1.0:
            military_weight = 1.0

        cv2.line(game_data, (0, 19), (int(line_max*military_weight), 19), (250, 250, 200), 3)  # worker/supply ratio
        cv2.line(game_data, (0, 15), (int(line_max*plausible_supply), 15), (220, 200, 200), 3)  # plausible supply (supply/200.0)
        cv2.line(game_data, (0, 11), (int(line_max*population_ratio), 11), (150, 150, 150), 3)  # population ratio (supply_left/supply)
        cv2.line(game_data, (0, 7), (int(line_max*vespene_ratio), 7), (210, 200, 0), 3)  # gas / 1500
        cv2.line(game_data, (0, 3), (int(line_max*mineral_ratio), 3), (0, 255, 25), 3)  # minerals minerals/1500

        # flip horizontally to make our final fix in visual representation:
        self.flipped = cv2.flip(game_data, 0)

        # if not HEADLESS:
        #     resized = cv2.resize(self.flipped, dsize=None, fx=2, fy=2)
        #     cv2.imshow('Intel', resized)
        #     cv2.waitKey(1)

    async def build_workers(self):
        if (len(self.units(NEXUS)) * 16) > len(self.units(PROBE)) and len(self.units(PROBE)) < self.MAX_WORKERS:
            for nexus in self.units(NEXUS).ready.noqueue:
                if self.can_afford(PROBE):
                    await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON):
            nexuses = self.units(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(PYLON, near=nexuses.first)

    async def build_assimilators(self):
        for nexus in self.units(NEXUS).ready:
            vaspenes = self.state.vespene_geyser.closer_than(15.0, nexus)
            for vaspene in vaspenes:
                if not self.can_afford(ASSIMILATOR):
                    break
                worker = self.select_build_worker(vaspene.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1.0, vaspene).exists:
                    await self.do(worker.build(ASSIMILATOR, vaspene))

    async def expand(self):
        if self.units(NEXUS).amount < (self.iteration / self.ITERATIONS_PER_MINUTE) and self.can_afford(NEXUS):
            await self.expand_now()

    async def offensive_force_buildings(self):
        #print(self.iteration / self.ITERATIONS_PER_MINUTE)
        if self.units(PYLON).ready.exists:
            pylon = self.units(PYLON).ready.random

            if self.units(GATEWAY).ready.exists and not self.units(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, near=pylon)

            elif len(self.units(GATEWAY)) < 1:
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=pylon)

            if self.units(CYBERNETICSCORE).ready.exists:
                if len(self.units(ROBOTICSFACILITY)) < 1:
                    if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
                        await self.build(ROBOTICSFACILITY, near=pylon)

            if self.units(CYBERNETICSCORE).ready.exists:
                if len(self.units(STARGATE)) < (self.iteration / self.ITERATIONS_PER_MINUTE):
                    if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
                        await self.build(STARGATE, near=pylon)

    async def build_offensive_force(self):
        for sg in self.units(STARGATE).ready.noqueue:
            if self.can_afford(VOIDRAY) and self.supply_left > 0:
                await self.do(sg.train(VOIDRAY))

    def find_target(self, state):
        if len(self.known_enemy_units) > 0:
            return random.choice(self.known_enemy_units)
        elif len(self.known_enemy_structures) > 0:
            return random.choice(self.known_enemy_structures)
        else:
            return self.enemy_start_locations[0]

    async def attack(self):
        if len(self.units(VOIDRAY).idle) > 0:
            choice = random.randrange(0, 4)
            target = False
            if self.iteration > self.do_something_after:
                if choice == 0:
                    # no attack
                    wait = random.randrange(20, 165)
                    self.do_something_after = self.iteration + wait

                elif choice == 1:
                    #attack_unit_closest_nexus
                    if len(self.known_enemy_units) > 0:
                        target = self.known_enemy_units.closest_to(random.choice(self.units(NEXUS)))

                elif choice == 2:
                    #attack enemy structures
                    if len(self.known_enemy_structures) > 0:
                        target = random.choice(self.known_enemy_structures)

                elif choice == 3:
                    #attack_enemy_start
                    target = self.enemy_start_locations[0]

                if target:
                    for vr in self.units(VOIDRAY).idle:
                        await self.do(vr.attack(target))
                y = np.zeros(4)
                y[choice] = 1
                print(y)
                self.train_data.append([y,self.flipped])
