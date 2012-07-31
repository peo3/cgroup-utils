# This test is based on http://d.hatena.ne.jp/tk0miya/20120623
import os
import os.path
import pep8
import sys


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DIRS = [os.path.join(CURRENT_DIR, 'bin'), os.path.join(CURRENT_DIR, 'cgutils')]

# This awkward will disappears once pep8 prioritizes ignore over select...
def generate_selects(ignores):
    ret = []
    for i in range(1, 10):
        e = "E%d" % i
        matched = [ig for ig in ignores if ig.startswith(e)]
        if len(matched) == 0:
            ret.append(e)
            continue
        ignores3 = [ig for ig in matched if len(ig) >= 3]
        if not ignores3:
            continue
        for j in range(0, 10):
            e = "E%d%d" % (i, j)
            matched = [ig for ig in ignores3 if ig.startswith(e)]
            if len(matched) == 0:
                ret.append(e)
                continue
            ignores4 = [ig for ig in matched if len(ig) >= 4]
            if not ignores4:
                continue
            for k in range(0, 10):
                e = "E%d%d%d" % (i, j, k)
                matched = [ig for ig in ignores4 if ig.startswith(e)]
                if len(matched) == 0:
                    ret.append(e)
    return ret


IGNORES = ['E501', 'E24']
SELECTS = generate_selects(IGNORES)


def test_pep8(dirs=DIRS):
    pep8style = pep8.StyleGuide(statistics=True,
                                show_source=True,
                                ignore=IGNORES,
                                select=SELECTS,
                                paths=dirs,
                                parse_argv=False)
    options = pep8style.options
    if options.doctest:
        import doctest
        fail_d, done_d = doctest.testmod(report=False, verbose=options.verbose)
        fail_s, done_s = selftest(options)
        count_failed = fail_s + fail_d
        if not options.quiet:
            count_passed = done_d + done_s - count_failed
            print("%d passed and %d failed." % (count_passed, count_failed))
            print("Test failed." if count_failed else "Test passed.")
        if count_failed:
            sys.exit(1)
    if options.testsuite:
        init_tests(pep8style)
    report = pep8style.check_files()
    if options.statistics:
        report.print_statistics()
    if options.benchmark:
        report.print_benchmark()
    if options.testsuite and not options.quiet:
        report.print_results()
    if report.total_errors:
        if options.count:
            sys.stderr.write(str(report.total_errors) + '\n')
        sys.exit(1)

    # reporting errors (additional summary)
    errors = report.get_count('E')
    warnings = report.get_count('W')
    message = 'pep8: %d errors / %d warnings' % (errors, warnings)
    print message
    assert report.total_errors == 0, message

if __name__ == '__main__':
    test_pep8(sys.argv[1:])
