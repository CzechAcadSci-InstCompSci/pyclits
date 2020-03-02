#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import pickle
import time
from pathlib import Path

import numpy as np
import scipy.interpolate

import data_plugin
from mutual_inf import renyi_transfer_entropy
from roessler_system import roessler_oscillator
from sample_generator import preparation_dataset_for_transfer_entropy

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calculates transfer entropy for coupled Rössler systems with strength of coupling epsilon.')
    parser.add_argument('--epsilon', metavar='XXX', type=float, nargs='+', help='Epsilons')
    parser.add_argument('--t_stop', metavar='XXX', type=float, default=10000.0, help='T stop')
    parser.add_argument('--t_inc', metavar='XXX', type=float, default=0.01, help='T increment')
    parser.add_argument('--no_cache', action='store_true', help='Skips cached results of the Rössler system')
    parser.add_argument('--skip', metavar='XXX', type=int, default=2000, help='Skipped results of integration')
    parser.add_argument('--blockwise', metavar='XXX', type=int, default=0, help='Blockwise calculation of distances to prevent excessive memory usage')
    parser.add_argument('--skip_real_t', action='store_true', help='Indicates skip in time')
    parser.add_argument('--history_first', metavar='XXX', type=int, nargs='+', help='History to take into account')
    parser.add_argument('--history_second', metavar='XXX', type=int, nargs='+', help='History to take into account')
    parser.add_argument('--method', metavar='XXX', type=str, default="LSODA", help='Method of integration')
    parser.add_argument('--maximal_neighborhood', metavar='XXX', type=int, default=2, help='Maximal neighborhood')
    parser.add_argument('--arbitrary_precision', action='store_true', help='Calculates the main part in arbitrary precision')
    parser.add_argument('--arbitrary_precision_decimal_places', metavar='XXX', type=int, default=100,
                        help='Sets number saved in arbitrary precision arithmetic')
    parser.add_argument('--interpolate', action='store_true', help='Switch on intepolation')
    parser.add_argument('--interpolate_samples_per_unit_time', metavar='XXX', type=int, default=10, help='Number of samples generated per unit time')
    parser.add_argument('--dataset', action='store_true', help='Use dataset provided by dr. Paluš')
    parser.add_argument('--dataset_range', metavar='XXX-YYY', type=str, help='Dataset with range')
    args = parser.parse_args()
    # print(args.epsilon, flush=True)

    if args.epsilon:
        epsilons = args.epsilon
    else:
        epsilons = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.11, 0.12, 0.13]

    # + 1 must be added to the history here because the actual timeserie is then stripped (-1)
    if args.history_first:
        histories_first = args.history_first
    else:
        histories_first = range(2, 25)

    if args.history_second:
        histories_second = args.history_second
    else:
        histories_second = range(2, 25)

    if args.dataset:
        print("Load dataset")
        datasets = data_plugin.load_datasets()

        if args.dataset_range:
            dataset_start = int(args.dataset_range.split("-")[0])
            dataset_end = int(args.dataset_range.split("-")[1])
            datasets = datasets[dataset_start:dataset_end]

        epsilons = []
        for dataset in datasets:
            epsilons.append(dataset[0]["eps1"])
        print(f"Epsilons: {epsilons}")

    for index_epsilon, epsilon in enumerate(epsilons):
        configuration = {"method": args.method, "tInc": args.t_inc, "tStop": args.t_stop, "cache": True, "epsilon": epsilon,
                         "arbitrary_precision": args.arbitrary_precision, "arbitrary_precision_decimal_numbers": args.arbitrary_precision_decimal_places}

        if not args.dataset:
            t0 = time.process_time()
            sol = roessler_oscillator(**configuration)
            t1 = time.process_time()
            duration = t1 - t0
            print(f"Solution duration [s]: {duration}", flush=True)

            if args.interpolate:
                number = int((args.t_stop - args.skip) * args.interpolate_samples_per_unit_time)

                new_t = np.linspace(args.skip, args.t_stop, num=number, endpoint=True)
                solution = []
                for dimension in range(sol.y.shape[0]):
                    function = scipy.interpolate.interp1d(sol.t, sol.y[dimension], kind='cubic')

                    solution.append(function(new_t))

                filtrated_solution = np.vstack(solution)
            else:
                # preparation of sources
                if args.skip_real_t:
                    indices = np.where(sol.t >= args.skip)
                    if len(indices) > 0:
                        filtrated_solution = sol.y[:, indices[0]:]
                    else:
                        logging.error("Skipping is too large and no data were selected for processing")
                        raise AssertionError("No data selected")
                else:
                    filtrated_solution = sol.y[:, args.skip:]

            print(f"Shape of solution: {filtrated_solution.shape}")
            joint_solution = filtrated_solution
            marginal_solution_1 = filtrated_solution[0:3, :].T
            marginal_solution_2 = filtrated_solution[3:6, :].T
        else:
            filtrated_solution = datasets[index_epsilon][1].T

            print(f"Shape of solution: {filtrated_solution.shape}")
            joint_solution = filtrated_solution
            marginal_solution_1 = filtrated_solution[0:1, :].T
            marginal_solution_2 = filtrated_solution[1:2, :].T

        alphas = np.linspace(0.1, 1.9, 19)
        results = {}
        for history_first in histories_first:
            for history_second in histories_second:
                print(f"History first: {history_first}, history second: {history_second} and epsilon: {epsilon} is processed", flush=True)

                solution_size = joint_solution.shape
                configuration = {"transpose": True, "history_x": history_first, "history_y": history_second, "blockwise": args.blockwise}

                t0 = time.process_time()
                y, y_hist, z = preparation_dataset_for_transfer_entropy(marginal_solution_2, marginal_solution_1, **configuration)
                t1 = time.process_time()
                duration = t1 - t0
                print(f" * Preparation of datasets [s]: {duration}", flush=True)

                indices_to_use = list(range(1, args.maximal_neighborhood + 1))
                configuration = {"transpose": True, "axis_to_join": 0, "method": "LeonenkoProzanto", "alphas": alphas,
                                 "enhanced_calculation": True, "indices_to_use": indices_to_use, "arbitrary_precision": args.arbitrary_precision,
                                 "arbitrary_precision_decimal_numbers": args.arbitrary_precision_decimal_places}

                print(f" * Transfer entropy for history first: {history_first}, history second: {history_second} and epsilon: {epsilon} is calculated",
                      flush=True)
                t0 = time.process_time()
                transfer_entropy = renyi_transfer_entropy(y, y_hist, z, **configuration)
                t1 = time.process_time()
                duration = t1 - t0
                print(f" * Duration of calculation of transfer entropy [s]: {duration}", flush=True)
                # print(f" * Transfer Renyi entropy with {history} {epsilon}: {transfer_entropy}", flush=True)

                results[(epsilon, history_first, history_second)] = transfer_entropy
                print(
                    f" * Transfer entropy calculation for history first: {history_first}, history second: {history_second} and epsilon: {epsilon} is finished",
                    flush=True)

        path = Path(f"transfer_entropy/Transfer_entropy_dataset-{epsilon}.bin")
        print(f"Save to file {path}", flush=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fb:
            pickle.dump(results, fb)
