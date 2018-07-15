from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from MyBots import ChaBot1, ChaBot2, SentdeBot, ChaBotDL


def main():
    run_game(maps.get("AbyssalReefLE"), [
        Bot(Race.Protoss, ChaBotDL()),
        Computer(Race.Random, Difficulty.Easy)
        # Bot(Race.Protoss, ChaBot2())
    ], realtime=False)

    return 0


if __name__ == '__main__':
    main()