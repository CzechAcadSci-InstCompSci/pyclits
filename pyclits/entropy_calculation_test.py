#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import time

import mutual_inf
from random_samples import *

time_start = time.process_time()


def complete_test_1D(filename="statistics.txt", samples=1000,
                     alphas=(0.1, 0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0, 1.01, 1.05, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9),
                     mu=0, sigmas=(0.1, 0.5, 1.0, 5.0, 10.0, 50, 100),
                     sizes_of_sample=(10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000),
                     theoretical_value_function=lambda sigma, alpha: Renyi_normal_distribution_1D(sigma, alpha),
                     sample_generator=lambda mu, sigma, size_sample: np.random.normal(mu, sigma, (size_sample, 1)),
                     sample_estimator=lambda data_samples, alpha: mutual_inf.renyi_entropy(data_samples, method="LeonenkoProzanto",
                                                                                           indices_to_use=[1, 2, 3, 4, 5], alpha=alpha)):
    with open(filename, "wt") as fd:
        entropy_samples = {}
        duration_samples = {}
        difference_samples = {}

        for sigma in sigmas:
            for alpha in alphas:
                for size_sample in sizes_of_sample:
                    sample_position = (alpha, size_sample, sigma)
                    theoretical_value = theoretical_value_function(sigma, alpha)

                    entropy_samples[sample_position] = []
                    duration_samples[sample_position] = []
                    difference_samples[sample_position] = []

                    for sample in range(1, samples + 1):
                        if sample % 10 == 0:
                            print(f"alpha = {alpha}, size_sample = {size_sample}, sigma={sigma}, sample = {sample}")

                        data_samples = sample_generator(mu, sigma, size_sample)

                        time_start = time.process_time()
                        entropy = sample_estimator(data_samples, alpha=alpha)
                        time_end = time.process_time()

                        duration = time_end - time_start
                        difference = theoretical_value - entropy

                        entropy_samples[sample_position].append(entropy)
                        duration_samples[sample_position].append(duration)
                        difference_samples[sample_position].append(difference)

                        # print(f"samples={size_sample}, duration={time_end-time_start}, alpha={alpha}, tested_estimator={entropy}, theoretical_calculation={theoretical_value}, difference={difference}")

                    print(
                        f"{alpha} {size_sample} {sigma} {np.mean(entropy_samples[sample_position])} {np.std(entropy_samples[sample_position])} {np.mean(duration_samples[sample_position])} {np.std(duration_samples[sample_position])} {np.mean(difference_samples[sample_position])} {np.std(difference_samples[sample_position])}",
                        file=fd)


def complete_test_ND(filename="statistics.txt", samples=1000, sigma_skeleton=np.identity(10),
                     alphas=(0.1, 0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0, 1.01, 1.05, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9),
                     mu=0, sigmas=(0.1, 0.5, 1.0, 5.0, 10.0, 50, 100),
                     sizes_of_sample=(10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000), indices_to_use=(1, 2, 3, 4, 5, 6, 7, 8, 9),
                     theoretical_value_function=lambda sigma, alpha, determinant: Renyi_normal_distribution_ND(sigma, alpha, determinant),
                     sample_generator=lambda mu, sigma, size_sample: sample_normal_distribution(sigma, size_sample),
                     sample_estimator=lambda data_samples, alpha, indices_to_use: mutual_inf.renyi_entropy(data_samples, method="LeonenkoProzanto",
                                                                                                           indices_to_use=indices_to_use, alpha=alpha),
                     determinant=None):
    dimension = sigma_skeleton.shape[0]
    with open(filename, "wt") as fd:
        real_indeces = []
        print("dimension\talpha\tsample size\tsigma\ttheoretical value\t", file=fd, end="")
        for index in indices_to_use:
            print(
                f"mean Renyi entropy {index}\tstd Renyi entropy {index}\tmean computer time {index}\tstd computer time {index}\tmean difference {index}\tstd of difference {index}\t3rd moment of difference {index}\t",
                file=fd, end="")
            real_indeces.append([index])
        print("mean Renyi entropy\tstd Renyi entropy\tmean computer time\tstd computer time\tmean difference\tstd of difference\t3rd moment of difference",
              file=fd)
        real_indeces.append(indices_to_use)

        # collections of results
        entropy_samples = {}
        duration_samples = {}
        difference_samples = {}

        for sigma in sigmas:
            matrix_sigma = sigma * sigma_skeleton

            used_determinant = determinant
            if determinant:
                # if determinant is precalculated the value have to be adjusted for sigma
                # mpmath is used because of extreme dimensions sizes
                used_determinant *= mpmath.power(sigma, dimension)

            for alpha in alphas:
                theoretical_value = theoretical_value_function(matrix_sigma, alpha, used_determinant)

                for size_sample in sizes_of_sample:
                    print(f"{dimension}\t{alpha}\t{size_sample}\t{sigma}\t{theoretical_value}\t", file=fd, end="")

                    for indices_to_use in real_indeces:
                        sample_position = (alpha, size_sample, sigma)

                        entropy_samples[sample_position] = []
                        duration_samples[sample_position] = []
                        difference_samples[sample_position] = []

                        for sample in range(1, samples + 1):
                            if sample % 10 == 0:
                                print(f"alpha = {alpha}, size_sample = {size_sample}, sigma={sigma}, sample = {sample}, indices_to_use={indices_to_use}")

                            data_samples = sample_generator(mu, matrix_sigma, size_sample)

                            time_start = time.process_time()
                            entropy = sample_estimator(data_samples, alpha={alpha}, indices_to_use=indices_to_use)
                            entropy_value = entropy[alpha][0]
                            time_end = time.process_time()

                            duration = time_end - time_start
                            difference = theoretical_value - entropy_value

                            entropy_samples[sample_position].append(entropy_value)
                            duration_samples[sample_position].append(duration)
                            difference_samples[sample_position].append(difference)

                        # save data for samples
                        print(
                            f"{np.mean(entropy_samples[sample_position])}\t{np.std(entropy_samples[sample_position])}\t{np.mean(duration_samples[sample_position])}\t{np.std(duration_samples[sample_position])}\t{np.mean(difference_samples[sample_position])}\t{np.std(difference_samples[sample_position])}\t{stat.moment(difference_samples[sample_position], moment=3)}\t",
                            file=fd, end="")
                    print("", file=fd, flush=True)


def small_test():
    sample_array = np.array([[1], [2], [3], [4], [5], [6], [7], [8], [9]], dtype=float)
    input_sample = np.ndarray(shape=sample_array.shape, buffer=sample_array)
    # print(input_sample)
    # print(mutual_inf.renyi_entropy(np.matrix([[1],[2],[3],[4],[5],[6],[7],[8],[9]]), method="LeonenkoProzanto"))
    # print(mutual_inf.renyi_entropy(input_sample, method="Paly"))

    mu = 0
    sigma = 10

    number_samples = 100
    alpha = 0.98
    alphas = [0.1, 0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0, 1.01, 1.05, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9]
    for alpha in alphas:
        for number_samples in [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]:
            entropy = 0
            data_samples = np.random.normal(mu, sigma, (number_samples, 1))
            time_start = time.process_time()
            # entropy = mutual_inf.renyi_entropy(samples, method="Lavicka", indices_to_use=[1])
            time_end = time.process_time()
            # print(number_samples, time_end-time_start, entropy, Renyi_normal_distribution_1D(sigma, alpha))

            time_start = time.process_time()
            entropy = mutual_inf.renyi_entropy(data_samples, method="LeonenkoProzanto", indices_to_use=[1, 2, 3, 4, 5], alpha=alpha)
            theoretical_value = Renyi_normal_distribution_1D(sigma, alpha)
            difference = abs(theoretical_value - entropy)
            time_end = time.process_time()
            print(
                f"samples={number_samples}, duration={time_end - time_start}, alpha={alpha}, tested_estimator={entropy}, theoretical_calculation={theoretical_value}, difference={difference}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Calculation of Renyi entropy using various methods')
    parser.add_argument('--output', metavar='XXX', type=str, default="complete_statistics_Paly", help='Base filename')
    parser.add_argument('--dimensions', metavar='XXX', type=int, nargs='+', help='Dimensions')
    parser.add_argument('--method', metavar='XXX', type=str, default="LeonenkoProzanto", help='Method of Renyi calculation')
    parser.add_argument('--alphas', metavar='XXX', type=float, nargs='+', help='Alpha')
    parser.add_argument('--samples', metavar='XXX', type=int, nargs='+', help='Sample sizes')
    parser.add_argument('--sigmas', metavar='XXX', type=float, nargs='+', help='Sigmas')
    parser.add_argument('--correlation', metavar='XXX', type=float, default=0.0, help='Correlation strength')
    parser.add_argument('--correlation_type', metavar='XXX', type=str, default="identity", help='Correlation matrix type')
    parser.add_argument('--maximal_index', metavar='XXX', type=int, default=3, help='Maximal index')
    parser.add_argument('--noise_type', metavar='XXX', type=str, default="gaussian", help='Type of noise that is to be investigated')
    parser.add_argument('--arbitrary_precision', metavar='XXX', type=bool, default=False, help='Use of the arbitrary precision')
    parser.add_argument('--arbitrary_precision_decimal_numbers', metavar='XXX', type=int, default="30", help='How many decimal numbers are used')
    parser.add_argument('--metric', metavar='XXX', type=str, default="euclidean", help='Metric')

    args = parser.parse_args()

    correlation_types = ["identity", "weakly_correlated", "strongly_correlated"]
    noise_types = ["gaussian", "student", "sub_gaussian"]
    output_filename = args.output
    method = args.method
    correlation = args.correlation
    correlation_type = args.correlation_type
    noise_type = args.noise_type
    indices = np.arange(1, args.maximal_index + 1)
    if correlation_type not in correlation_types:
        raise SystemExit("Wrong type correlation type")

    if noise_type not in noise_types:
        raise SystemExit("Wrong type correlation type")

    if args.dimensions:
        dimensions = args.dimensions
    else:
        dimensions = [2, 3, 5, 10, 20, 50]

    if args.samples:
        samples_sizes = args.samples
    else:
        samples_sizes = [500, 5000, 50000]

    if args.sigmas:
        sigmas = args.sigmas
    else:
        sigmas = [1.0]

    if args.alphas:
        alphas = args.alphas
    else:
        # alphas = [0.1, 0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0, 1.01, 1.05, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9]
        # alphas = [0.51, 0.55, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]

        alphas = [0.1, 0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0, 1.01, 1.05, 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 1.9]


    arbitrary_precision = args.arbitrary_precision
    arbitrary_precision_decimal_numbers = args.arbitrary_precision_decimal_numbers
    use_metric = args.metric
    degrees_of_freedom = 3
    alpha = 2.0

    job_dictionary = {"gaussian": {"generator": lambda mu, sigma, size_sample: sample_normal_distribution(sigma, size_sample),
                                   "theory": lambda sigma, alpha, determinant: Renyi_normal_distribution_ND(sigma, alpha, determinant)},
                      "student": {"generator": lambda mu, sigma, size_sample: sample_student_t_distribution(degrees_of_freedom, sigma, mu, size_sample),
                                  "theory": lambda sigma, alpha, determinant: Renyi_student_t_distribution(degrees_of_freedom, sigma, alpha, determinant)},
                      "sub_gaussian": {"generator": lambda mu, sigma, size_sample: sample_elliptical_contour_stable(sigma, alpha, mu, size_sample),
                                       "theory": None}}
    estimator_dictionary = {"Renyi": lambda data_samples, alpha, indices_to_use: mutual_inf.renyi_entropy(data_samples, method=method,
                                                                                                          indices_to_use=indices_to_use, alphas=alpha,
                                                                                                          **{"arbitrary_precision": arbitrary_precision,
                                                                                                             "arbitrary_precision_decimal_numbers": arbitrary_precision_decimal_numbers,
                                                                                                             "metric": use_metric})}

    print(f"Calculation for dimensions {dimensions}")

    for dimension in dimensions:
        sigma_skeleton = None
        determinant = None
        if correlation_type in correlation_types[0]:
            sigma_skeleton = np.identity(dimension)
            determinant = 1.
        elif correlation_type in correlation_types[1]:
            sigma_skeleton = np.identity(dimension) + correlation * np.eye(dimension, k=1) + correlation * np.eye(dimension, k=-1)
            determinant = tridiagonal_matrix_determinant(dimension, correlation)
        elif correlation_type in correlation_types[2]:
            sigma_skeleton = None
            determinant = pow(1 - correlation, dimension) * (1 + dimension * correlation)

        complete_test_ND(filename=f"{output_filename}_{dimension}.txt", samples=3, sigmas=sigmas, alphas=alphas,
                         sigma_skeleton=sigma_skeleton, sizes_of_sample=samples_sizes, indices_to_use=indices,
                         theoretical_value_function=job_dictionary[noise_type]["theory"],
                         sample_generator=job_dictionary[noise_type]["generator"],
                         sample_estimator=estimator_dictionary["Renyi"], determinant=determinant)
