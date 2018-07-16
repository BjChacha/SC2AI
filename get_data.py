from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot
from MyBots import ChaBotDL
import sys

def main(argv):
    iterations = argv[0]
    for i in range(int(iterations[1])):
        print('game {0} begin.'.format(i+1))
        run_game(maps.get("AbyssalReefLE"), [
            Bot(Race.Protoss, ChaBotDL()),
            Bot(Race.Protoss, ChaBotDL())
        ], realtime=False)
        print('game {0} over.'.format(i+1))

    return 0

if __name__ == "__main__":
    main([sys.argv])