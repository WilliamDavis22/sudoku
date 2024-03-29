import imageio
import numpy as np

from generator import base_numbers
from generator.Generator import Generator
from ocr.ocr_detector import get_detector
from ocr.ocr_recognizer import get_recognizer


def load_model():
    detector_model_h5 = "/Users/wdavis4/__pycache__/lecture0/sudoku_solver/solver/ocr_detector.h5"
    detector_model = get_detector()
    detector_model.load_weights(detector_model_h5)

    recognizer_model_h5 = "/Users/wdavis4/__pycache__/lecture0/sudoku_solver/solver/ocr_recognizer.h5"
    recognizer_model = get_recognizer()
    recognizer_model.load_weights(recognizer_model_h5)
    return detector_model, recognizer_model


def read_img_from_path(path):
    img = imageio.imread(path, pilmode="RGB")
    return img


def read_from_file(file_object):
    img = imageio.imread(file_object, pilmode="RGB")

    return img


def replace_with_zeros(x_arr, ratio=0.5):
    out = []
    for x in x_arr:
        row = []
        for z in x:
            if np.random.uniform(0, 1) < ratio:
                row.append(z)
            else:
                row.append(0)
        out.append(row)

    return out


def get_sample(random_replace=True):
    gen = Generator(base_numbers, shuffle_base=True)
    gen.randomize(np.random.randint(20, 1000))
    initial = gen.board.copy()
    x_out = [[a.value for a in x] for x in initial.rows.values()]

    gen.reduce_via_logical(np.random.randint(31, 360))

    removed = gen.board.copy()

    x_in = [[a.value for a in x] for x in removed.rows.values()]

    if random_replace:
        x_in = replace_with_zeros(x_in, ratio=np.random.uniform(0.6, 0.9))

    return x_in, x_out


def binarize_along_last_axis(arr, n_classes=10):
    out = np.zeros(arr.shape + (n_classes,))
    for i in range(n_classes):
        out[..., i] = (arr == i).astype(np.float)

    return out


def gen(batch_size=64):
    while True:
        samples = [get_sample(random_replace=True) for _ in range(batch_size)]
        X, Y = zip(*samples)
        X = np.array(X)
        Y = np.array(Y)

        X = binarize_along_last_axis(X, n_classes=10)
        Y = binarize_along_last_axis(Y, n_classes=10)

        yield X, Y


def predict_sequential_deterministic(arr, model):
    X_in = np.array(arr)

    while np.sum(X_in == 0):
        X = X_in[np.newaxis, ...]
        X = binarize_along_last_axis(X, n_classes=10)

        pred = model.predict(X).squeeze()
        pred[..., 0] = -1000

        pred_max = pred.max(axis=-1)
        pred_argmax = pred.argmax(axis=-1)

        i_all, j_all = np.where(X_in == 0)
        max_idx = pred_max[X_in == 0].argmax()
        i, j = i_all[max_idx], j_all[max_idx]

        X_in[i, j] = pred_argmax[i, j]

    sodoku_gen = Generator(X_in.ravel().tolist())

    return sodoku_gen


def predict_sequential_random(arr, model):
    X_in = np.array(arr)

    while np.sum(X_in == 0):
        X = X_in[np.newaxis, ...]
        X = binarize_along_last_axis(X, n_classes=10)

        pred = model.predict(X).squeeze()
        pred = pred + np.random.normal(0, 0.1, size=pred.shape)
        pred[..., 0] = -1000

        pred_max = pred.max(axis=-1)
        pred_argmax = pred.argmax(axis=-1)

        i_all, j_all = np.where(X_in == 0)
        max_idx = pred_max[X_in == 0].argmax()
        i, j = i_all[max_idx], j_all[max_idx]

        X_in[i, j] = pred_argmax[i, j]

    sodoku_gen = Generator(X_in.ravel().tolist())

    return sodoku_gen


def predict(arr, model):
    x_in = [arr]

    X_in = np.array(x_in)
    X_in = binarize_along_last_axis(X_in, n_classes=10)

    pred = model.predict(X_in)
    pred = pred.argmax(axis=-1)

    pred_gen = Generator(pred[0, ...].ravel().tolist())

    return pred_gen


def solve_sudoku(arr, model):
    pred_gen = predict(arr, model)

    if pred_gen.board.is_solved():
        print("Solved in one shot")
        return pred_gen
    else:
        pred_gen = predict_sequential_deterministic(arr, model)
        if pred_gen.board.is_solved():
            print("Solved sequentially")
            return pred_gen
        else:
            max_count = 10
            for i in range(max_count):
                pred_gen = predict_sequential_random(arr, model)
                if pred_gen.board.is_solved():
                    print("Solved sequentially random")
                    return pred_gen

    print("Could not be solved")
    return pred_gen


def set_initially_available(cells):
    for cell in cells:
        if cell.value == 0:
            cell.initially_available = False
        else:
            cell.initially_available = True


def backtracking_solve(board):
    # Modified from https://github.com/RutledgePaulV/sudoku-generator/blob/master/Sudoku/Solver.py
    set_initially_available(board.cells)
    to_be_filled = board.get_unused_cells()
    index = 0
    n_iter = 0
    while -1 < index < len(to_be_filled):
        current = to_be_filled[index]
        flag = False
        possible_values = board.get_possibles(current)
        my_range = range(current.value + 1, 10)
        for x in my_range:
            if x in possible_values:
                n_iter += 1
                current.value = x
                flag = True
                break
        if not flag:
            current.value = 0
            index -= 1
        else:
            index += 1
    if len(to_be_filled) == 0:
        return n_iter, False
    else:
        return n_iter, index == len(to_be_filled)
