import time
def write_log(message, game_status = None, game_board = None):        
    with open("debugs.txt",'a') as f:
        cur_time = time.time()  
        f.write(f"LOGGER: [INFOR] [{cur_time}]: Message: {message} Game status {game_status} Game board {game_board}\n")