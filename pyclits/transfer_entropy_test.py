#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import pickle
import time
from pathlib import Path

import numpy as np

from mutual_inf import renyi_transfer_entropy
from roessler_system import roessler_oscillator
from sample_generator import preparation_dataset_for_transfer_entropy

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calculates transfer entropy for coupled Rössler systems with strength of coupling epsilon.')
    parser.add_argument('--epsilon', metavar='XXX', type=float, nargs='+', help='Epsilons')
    parser.add_argument('--t_stop', metavar='XXX', type=float, default=10000.0, help='T stop')
    parser.add_argument('--t_inc', metavar='XXX', type=float, default=0.001, help='T increment')
    parser.add_argument('--skip', metavar='XXX', type=int, default=2000, help='Skipped results of integration')
    parser.add_argument('--history', metavar='XXX', type=int, nargs='+', help='Historie to take into account')
    parser.add_argument('--method', metavar='XXX', type=str, default="LSODA", help='Method of integration')
    args = parser.parse_args()
    # print(args.epsilon, flush=True)

    if args.epsilon:
        epsilons = args.epsilon
    else:
        epsilons = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.11, 0.12, 0.13]

    if args.history:
        histories = args.history
    else:
        histories = range(2, 25)
        # [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15, 17, 20]

    for epsilon in epsilons:
        configuration = {"method": args.method, "tInc": args.t_inc, "tStop": args.t_stop, "cache": True, "epsilon": epsilon}

        t0 = time.process_time()
        sol = roessler_oscillator(**configuration)
        t1 = time.process_time()
        duration = t1 - t0
        print(f"Solution duration [s]: {duration}", flush=True)

        # preparation of sources
        filtrated_solution = sol.y[:, args.skip:]
        print(f"Shape of solution: {filtrated_solution.shape}")
        joint_solution = filtrated_solution
        marginal_solution_1 = filtrated_solution[0:3, :].T
        marginal_solution_2 = filtrated_solution[3:6, :].T

        alphas = np.linspace(0.01, 1.99, 199)
        results = {}
        for history in histories:
            print(f"History: {history} and epsilon: {epsilon} is processed", flush=True)
            solution_size = joint_solution.shape
            configuration = {"transpose": True, "history_x": history, "history_y": history}

            t0 = time.process_time()
            y, y_hist, z = preparation_dataset_for_transfer_entropy(marginal_solution_2, marginal_solution_1,
                                                                    **configuration)
            t1 = time.process_time()
            duration = t1 - t0
            print(f" * Preparation of datasets [s]: {duration}", flush=True)

            indices_to_use = list(range(1, 50))
            configuration = {"transpose": True, "axis_to_join": 0, "method": "LeonenkoProzanto", "alphas": alphas,
                             "enhanced_calculation": True, "indices_to_use": indices_to_use}

            print(f" * Transfer entropy for history: {history} and epsilon: {epsilon} is calculated", flush=True)
            t0 = time.process_time()
            transfer_entropy = renyi_transfer_entropy(y, y_hist, z, **configuration)
            t1 = time.process_time()
            duration = t1 - t0
            print(f" * Duration of calculation of transfer entropy [s]: {duration}", flush=True)
            # print(f" * Transfer Renyi entropy with {history} {epsilon}: {transfer_entropy}", flush=True)

            results[(epsilon, history)] = transfer_entropy
            print(f" * Transfer entropy calculation for history: {history} and epsilon: {epsilon} is finished", flush=True)

        path = Path(f"transfer_entropy/Transfer_entropy-{epsilon}.bin")
        print(f"Save to file {path}", flush=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fb:
            pickle.dump(results, fb)
