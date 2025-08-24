import pychrome
import re
import chess
import chess.engine
import keyboard
import pyautogui

STOCKFISH_PATH = ""

browser = pychrome.Browser(url="http://127.0.0.1:9222")
tab = browser.list_tab()[0]
tab.start()
tab.Runtime.enable()

top_left = None
bottom_right = None
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

def get_fen(user_color):
    res = tab.Runtime.evaluate(expression="""
    (() => {
      const el = document.querySelector("cg-board");
      return el ? el.innerHTML : "";
    })()
    """)
    board_html = res["result"].get("value", "")

    piece_map = {
        "pawn": chess.PAWN,
        "rook": chess.ROOK,
        "knight": chess.KNIGHT,
        "bishop": chess.BISHOP,
        "queen": chess.QUEEN,
        "king": chess.KING
    }

    square_size = 61.8182
    board = chess.Board(None)

    for color, name, x, y in re.findall(r'<piece class="(white|black) (\w+)" style="transform: translate\(([\d\.]+)px, ([\d\.]+)px\);">', board_html):
        file = int(round(float(x) / square_size))
        rank = 7 - int(round(float(y) / square_size))

        if user_color == "black":
            file = 7 - file
            rank = 7 - rank

        square = chess.square(file, rank)
        piece = chess.Piece(piece_map[name], color=="white")
        board.set_piece_at(square, piece)

    board.turn = chess.WHITE if user_color == "white" else chess.BLACK
    print(board)
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

def make_move():
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

        board = get_fen(user_color)

        if engine is None:
            start_engine()

        try:
            result = engine.play(board, chess.engine.Limit(time=0.1))
        except (chess.engine.EngineTerminatedError, chess.engine.EngineError, BrokenPipeError):
            print("Engine crashed — restarting...")
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
            print("Move played:", move.uci())
        else:
            print("Corners not set")

    except Exception as e:
        print("Unable to make move:", e)

keyboard.add_hotkey("ctrl+q", make_move)
keyboard.add_hotkey("ctrl+1", set_top_left)
keyboard.add_hotkey("ctrl+2", set_bottom_right)

print("ctrl+1 = set top left, ctrl+2 = set bottom right, ctrl+q = play move")
start_engine()
keyboard.wait()
