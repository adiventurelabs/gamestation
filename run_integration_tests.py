#!/usr/bin/env python3
"""
PlayStation Console Integration Test Runner.
Executes the full suite of unit and end-to-end integration tests,
verifying physical disc auto-detection, SYSTEM.CNF parsing, emulator launching,
controller exit shortcuts, debouncing, and error handling using realistic dummy files.
"""

import sys
import time
import unittest


def main():
    print("=" * 70)
    print("   PlayStation Console Automation - Full Integration Test Suite")
    print("=" * 70)
    print("Running automated tests across all subsystems:")
    print(" - Disc Auto-Detection & Hardware Ready Wait (Mock Optical Drive)")
    print(" - PlayStation Generation Identification (SYSTEM.CNF BOOT vs BOOT2)")
    print(" - Serial Extraction & Offline Game Title Resolution")
    print(" - DuckStation (PS1) & PCSX2 (PS2) Physical CLI Argument Construction")
    print(" - End-to-End Simulation: Insert -> Identify -> Launch -> Controller Exit")
    print(" - Duplicate Event Hardware Debouncing & Session Protection")
    print(" - Non-Game (DVD-Video / Audio CD) & Corrupt Disc Rejection")
    print("=" * 70)
    print()

    start_time = time.time()
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    elapsed = time.time() - start_time
    print()
    print("=" * 70)
    print(f"Tests executed: {result.testsRun}")
    print(f"Passed:         {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures:       {len(result.failures)}")
    print(f"Errors:         {len(result.errors)}")
    print(f"Elapsed Time:   {elapsed:.3f} seconds")
    print("=" * 70)

    if result.wasSuccessful():
        print("\n>>> ALL INTEGRATION AND UNIT TESTS PASSED SUCCESSFULLY! <<<\n")
        return 0
    else:
        print("\n>>> SOME TESTS FAILED! <<<\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
