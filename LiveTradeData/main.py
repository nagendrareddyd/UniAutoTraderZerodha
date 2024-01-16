import multiprocessing
import TicksAndOrders

if __name__ == '__main__':

    process1 = multiprocessing.Process(target=TicksAndOrders.startTicksData)

    process1.start()

    process1.join()