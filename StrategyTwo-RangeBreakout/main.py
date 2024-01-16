import multiprocessing
import startStrategy
from loggingConfig import setup_logging

if __name__ == '__main__':

    process1 = multiprocessing.Process(target=startStrategy.startStrategyProcess)
    process2 = multiprocessing.Process(target=startStrategy.startMonitoringPositions)
       
    process1.start()
    process2.start()
    
    process1.join()
    process2.join()