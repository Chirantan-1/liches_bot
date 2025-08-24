import pychrome
import re
import chess
import chess.engine
import keyboard
import pyautogui
import time
import json

STOCKFISH_PATH = ""

browser = pychrome.Browser(url="http://127.0.0.1:9222")
tab = browser.list_tab()[0]
tab.start()
tab.Runtime.enable()

top_left = None
bottom_right = None
running = False
engine = None

def start_engine():
    global engine
    try:
        if engine:
            engine.quit()
    except:
        pass
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    print("Engine started")

def set_top_left():
    global top_left
    top_left = pyautogui.position()
    print("Top left set:", top_left)

def set_bottom_right():
    global bottom_right
    bottom_right = pyautogui.position()
    print("Bottom right set:", bottom_right)

def get_board_from_moves():
    res = tab.Runtime.evaluate(expression="""
    (() => {
      const list = [...document.querySelectorAll("kwdb")].map(e => e.textContent.trim());
      return JSON.stringify(list);
    })()
    """)
    moves_json = res["result"].get("value", "[]")
    try:
        moves = json.loads(moves_json)
    except:
        moves = []
    board = chess.Board()
    for mv in moves:
        if not mv:
            continue
        try:
            board.push_san(mv)
        except Exception:
            try:
                cleaned = re.sub(r'[^\w=+#xRNBQKProm\-]', '', mv)
                board.push_san(cleaned)
            except Exception:
                break
    return board

def square_to_screen(file, rank, user_color):
    if top_left is None or bottom_right is None:
        print("Corners not set")
        return None
    x1, y1 = top_left
    x2, y2 = bottom_right
    width = (x2 - x1) / 8
    height = (y2 - y1) / 8
    if user_color == "black":
        file = 7 - file
        rank = 7 - rank
    cx = int(x1 + file * width + width/2)
    cy = int(y1 + (7-rank) * height + height/2)
    return (cx, cy)

def is_user_turn():
    res = tab.Runtime.evaluate(expression="""
    (() => {
        const el = document.querySelector(".rclock.rclock-turn.rclock-bottom .rclock-turn__text");
        return el ? el.innerText : "";
    })()
    """)
    return res["result"].get("value", "") == "Your turn"

def handle_promotion(to_file, to_rank, user_color, promotion_piece):
    if promotion_piece == chess.QUEEN:
        pos = square_to_screen(to_file, to_rank, user_color)
        pyautogui.click(pos)
    elif promotion_piece == chess.KNIGHT:
        pos = square_to_screen(to_file, to_rank-1, user_color)
        pyautogui.click(pos)
    elif promotion_piece == chess.ROOK:
        pos = square_to_screen(to_file, to_rank-2, user_color)
        pyautogui.click(pos)
    elif promotion_piece == chess.BISHOP:
        pos = square_to_screen(to_file, to_rank-3, user_color)
        pyautogui.click(pos)

def play_best_move():
    global engine
    try:
        res = tab.Runtime.evaluate(expression="""
        (() => {
            const el = document.querySelector("coords");
            if (!el) return "";
            return el.className;
        })()
        """)
        class_name = res["result"].get("value", "")
        user_color = "white" if class_name == "ranks" else "black"
        board = get_board_from_moves()
        if engine is None:
            start_engine()
        result = engine.play(board, chess.engine.Limit(time=0.1))
        move = result.move
        from_file = chess.square_file(move.from_square)
        from_rank = chess.square_rank(move.from_square)
        to_file = chess.square_file(move.to_square)
        to_rank = chess.square_rank(move.to_square)
        from_pos = square_to_screen(from_file, from_rank, user_color)
        to_pos = square_to_screen(to_file, to_rank, user_color)
        if from_pos and to_pos:
            pyautogui.click(from_pos)
            pyautogui.click(to_pos)
            if move.promotion:
                handle_promotion(to_file, to_rank, user_color, move.promotion)
            print("Move played:", move.uci())
    except (chess.engine.EngineTerminatedError, chess.engine.EngineError, BrokenPipeError):
        print("Engine crashed — restarting...")
        start_engine()
    except Exception as e:
        print("Unexpected error:", e)

def loop():
    global running
    while running:
        if is_user_turn():
            play_best_move()
        time.sleep(1)

def toggle():
    global running
    running = not running
    if running:
        print("Started")
        start_engine()
        loop()
    else:
        print("Stopped")
        if engine:
            try:
                engine.quit()
            except:
                pass

keyboard.add_hotkey("ctrl+1", set_top_left)
keyboard.add_hotkey("ctrl+2", set_bottom_right)
keyboard.add_hotkey("ctrl+3", toggle)

print("ctrl+1 = set top left, ctrl+2 = set bottom right, ctrl+3 = start/stop")
keyboard.wait()
