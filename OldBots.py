import random
from sc2 import BotAI, Result, position
from sc2.constants import (ASSIMILATOR, CYBERNETICSCORE, GATEWAY, IMMORTAL,
                           NEXUS, OBSERVER, PROBE, PYLON, ROBOTICSFACILITY,
                           STALKER, STARGATE, VOIDRAY)


class ChaBot(BotAI):
    # Bot only using Stalker and Voidray
    def __init__(self):
        self.ITERATIONS_PER_MINUTE = 165
        self.MAX_WORKERS = 60
        self.MAX_ASSIMILATORS = 4
        self.MAX_NEXUS = 4
        self.MAX_GATEWAY = 2
        self.MAX_STARGATE = 3
        self.EXPAND_TIMEGAP = 2
        self.FIRST_ATTACK_UNIT = STALKER
        self.SECOND_ATTACK_UNIT = VOIDRAY

    async def on_step(self, iteration):
        self.iteration = iteration
        # print("{0:.2f}".format(self.iteration / self.ITERATIONS_PER_MINUTE))
        await self.distribute_workers()
        await self.build_workers(max_amount=self.MAX_WORKERS)
        await self.build_pylons(iteration / self.ITERATIONS_PER_MINUTE // 4 + 5)
        await self.build_assimilators(max_amount=self.MAX_ASSIMILATORS)
        await self.expand(max_amount=self.MAX_NEXUS, expand_timegap=self.EXPAND_TIMEGAP)
        await self.offensive_force_building(max_amount_of_gateway=self.MAX_GATEWAY, max_amount_of_stargate=self.MAX_STARGATE)
        await self.train_offensive_force()
        await self.attack(defend_amount=5, attack_amount=28)

    async def build_workers(self, max_amount):
        for nexus in self.units(NEXUS).ready.noqueue:
            if self.can_afford(PROBE) and self.units(PROBE).amount / self.units(NEXUS).amount <= 16 and self.units(PROBE).amount < max_amount:
                await self.do(nexus.train(PROBE))

    async def build_pylons(self, supply_offset=5):
        if self.supply_cap < 200 and self.supply_left < supply_offset and not self.already_pending(PYLON):
            nexuses = self.units(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(PYLON, near=nexuses.first)

    async def build_assimilators(self, max_amount, amount_per_nexus=2):
        for nexus in self.units(NEXUS).ready:
            if self.units(PYLON).ready and self.units(GATEWAY).ready:
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

    async def offensive_force_building(self, max_amount_of_gateway, max_amount_of_stargate):
        if self.units(PYLON).ready.exists:
            # Build Cybernetics Core
            if self.units(GATEWAY).ready.exists and not (self.units(CYBERNETICSCORE).exists or self.already_pending(CYBERNETICSCORE)):
                if self.can_afford(CYBERNETICSCORE):
                    pylon = self.units(PYLON).ready.random
                    await self.build(CYBERNETICSCORE, near=pylon)
            # Build Gate Way
            elif self.units(GATEWAY).amount / self.units(NEXUS).ready.amount < 2 and self.units(GATEWAY).amount < max_amount_of_gateway:
                if self.can_afford(GATEWAY):
                    pylon = self.units(PYLON).ready.random
                    await self.build(GATEWAY, near=pylon)
            # Build Star Gate
            elif self.units(CYBERNETICSCORE).ready.exists and self.iteration / self.ITERATIONS_PER_MINUTE > 2 and self.units(STARGATE).amount < max_amount_of_stargate:
                if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
                    pylon = self.units(PYLON).ready.random
                    await self.build(STARGATE, near=pylon)

    async def train_offensive_force(self):
        if self.units(CYBERNETICSCORE).ready:
            for sg in self.units(STARGATE).ready.noqueue:
                if self.can_afford(self.SECOND_ATTACK_UNIT) and self.supply_left > 3 :
                    await self.do(sg.train(self.SECOND_ATTACK_UNIT))
            for gw in self.units(GATEWAY).ready.noqueue:
                if self.can_afford(self.FIRST_ATTACK_UNIT) and self.supply_left > 1 and (self.units(self.FIRST_ATTACK_UNIT).amount < 21 or self.units(self.FIRST_ATTACK_UNIT).amount // self.units(self.SECOND_ATTACK_UNIT).amount < 3):
                    await self.do(gw.train(self.FIRST_ATTACK_UNIT))

    async def attack(self, defend_amount, attack_amount):
        if self.units(self.FIRST_ATTACK_UNIT).amount + self.units(self.SECOND_ATTACK_UNIT).amount >= attack_amount:
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
            for s in self.units(self.FIRST_ATTACK_UNIT).idle:
                if self.known_enemy_units:
                    await self.do(s.attack(random.choice(self.known_enemy_units)))
            for v in self.units(self.SECOND_ATTACK_UNIT).idle:
                if self.known_enemy_units:
                    await self.do(v.attack(random.choice(self.known_enemy_units)))


class ChaBot2(BotAI):
    # Bot only using Stalker and Immortal
    def __init__(self):
        self.ITERATIONS_PER_MINUTE = 165
        self.MAX_WORKERS = 60
        self.MAX_ASSIMILATORS = 3
        self.MAX_NEXUS = 4
        self.MAX_GATEWAY = 2
        self.MAX_ROBOTICSFACILITY = 2
        self.EXPAND_TIMEGAP = 1.5
        self.FIRST_ATTACK_UNIT = STALKER
        self.SECOND_ATTACK_UNIT = IMMORTAL

    async def on_step(self, iteration):
        self.iteration = iteration
        # print("{0:.2f}".format(self.iteration / self.ITERATIONS_PER_MINUTE))
        await self.distribute_workers()
        await self.build_workers(max_amount=self.MAX_WORKERS)
        await self.build_pylons(iteration / self.ITERATIONS_PER_MINUTE // 4 + 5)
        await self.build_assimilators(max_amount=self.MAX_ASSIMILATORS)
        await self.expand(max_amount=self.MAX_NEXUS, expand_timegap=self.EXPAND_TIMEGAP)
        await self.offensive_force_building(max_amount_of_gateway=self.MAX_GATEWAY, max_amount_of_roboticsfacility=self.MAX_ROBOTICSFACILITY)
        await self.train_offensive_force()
        await self.attack(defend_amount=5, attack_amount=28)


    async def build_workers(self, max_amount):
        for nexus in self.units(NEXUS).ready.noqueue:
            if self.can_afford(PROBE) and self.units(PROBE).amount / self.units(NEXUS).amount <= 16 and self.units(PROBE).amount < max_amount:
                await self.do(nexus.train(PROBE))

    async def build_pylons(self, supply_offset=5):
        if self.supply_cap < 200 and self.supply_left < supply_offset and not self.already_pending(PYLON):
            nexuses = self.units(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(PYLON, near=nexuses.first)

    async def build_assimilators(self, max_amount, amount_per_nexus=2):
        for nexus in self.units(NEXUS).ready:
            if self.units(PYLON).ready and self.units(GATEWAY).ready:
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

    async def offensive_force_building(self, max_amount_of_gateway, max_amount_of_roboticsfacility):
        if self.units(PYLON).ready.exists:
            # Build Cybernetics Core
            if self.units(GATEWAY).ready.exists and not (self.units(CYBERNETICSCORE).exists or self.already_pending(CYBERNETICSCORE)):
                if self.can_afford(CYBERNETICSCORE):
                    pylon = self.units(PYLON).ready.random
                    await self.build(CYBERNETICSCORE, near=pylon)
            # Build Gate Way
            elif self.units(GATEWAY).amount / self.units(NEXUS).ready.amount < 2 and self.units(GATEWAY).amount < max_amount_of_gateway:
                if self.can_afford(GATEWAY):
                    pylon = self.units(PYLON).ready.random
                    await self.build(GATEWAY, near=pylon)
            # Build Robotics Facility
            elif self.units(CYBERNETICSCORE).ready.exists and self.iteration / self.ITERATIONS_PER_MINUTE > 2 and self.units(ROBOTICSFACILITY).amount < max_amount_of_roboticsfacility:
                if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
                    pylon = self.units(PYLON).ready.random
                    await self.build(ROBOTICSFACILITY, near=pylon)

    async def train_offensive_force(self):
        if self.units(CYBERNETICSCORE).ready:
            for sg in self.units(ROBOTICSFACILITY).ready.noqueue:
                if self.can_afford(IMMORTAL) and self.supply_left > 3 :
                    await self.do(sg.train(IMMORTAL))
            for gw in self.units(GATEWAY).ready.noqueue:
                if self.can_afford(STALKER) and self.supply_left > 1 and (self.units(STALKER).amount < 21 or self.units(STALKER).amount // self.units(IMMORTAL).amount < 3):
                    await self.do(gw.train(STALKER))

    async def attack(self, defend_amount, attack_amount):
        if self.units(STALKER).amount + self.units(IMMORTAL).amount >= attack_amount:
            for s in self.units(STALKER).idle:
                if self.known_enemy_structures:
                    await self.do(s.attack(random.choice(self.known_enemy_structures)))
                else:
                    await self.do(s.attack(self.enemy_start_locations[0]))
            for i in self.units(IMMORTAL).idle:
                if self.known_enemy_structures:
                    await self.do(i.attack(random.choice(self.known_enemy_structures)))
                else:
                    await self.do(i.attack(self.enemy_start_locations[0]))

        elif self.units(STALKER).amount + self .units(IMMORTAL).amount >= defend_amount:
            for s in self.units(STALKER).idle:
                if self.known_enemy_units:
                    await self.do(s.attack(random.choice(self.known_enemy_units)))
            for i in self.units(IMMORTAL).idle:
                if self.known_enemy_units:
                    await self.do(i.attack(random.choice(self.known_enemy_units)))
