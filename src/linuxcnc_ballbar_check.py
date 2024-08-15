from __future__ import annotations

import sys

import linuxcnc
import time


class BallbarCheck(object):
    def __init__(self) -> None:
        super().__init__()
        self.stat = linuxcnc.stat()
        self.command = linuxcnc.command()

        self.radius = 267.939  # in mm
        self.goto_feed = 1000  # goto position feed
        self.operation_feed = 1000  # operation feed
        self.num_times = 1  # number of times to run it

    def ready(self) -> bool:
        self.stat.poll()
        return (
            not self.stat.estop
            and self.stat.enabled
            and (self.stat.homed.count(1) == self.stat.joints)
            and (self.stat.interp_state == linuxcnc.INTERP_IDLE)
        )

    def cmd(self, cmd: str) -> None:
        print(cmd)
        self.command.mdi(cmd)
        self.command.wait_complete()  # wait until mode switch executed
        while not self.ready():
            continue

    def prep_run(self) -> None:
        self.command.mode(linuxcnc.MODE_MDI)
        self.command.wait_complete()  # wait until mode switch executed

        self.cmd("G17")  # Select the XY plane
        self.cmd("G90")  # Absolute distance mode

        self.cmd("G53 G0 Z1")  # Move Z to the machine safe height offset by 1mm
        self.cmd("G54")  # select the G54 coordinate system
        self.cmd(
            f"G0 X{self.radius + 1} Y0"
        )  # Move in the XY plane to the starting position

        self.cmd("G0 Z0")

    def do_run(self) -> None:
        # We set the feed that we'll be operating the rotation.
        # We might set this to other speeds depending on what we are measuring
        self.cmd(f"G1 F{self.operation_feed}")

        time.sleep(1)

        self.cmd(f"G1 X{self.radius}")  # move in 1.0mm

        # Initiate the circular motion
        self.cmd(f"G03 I-{self.radius} J0 P{self.num_times}")

        self.cmd(f"G1 X{self.radius + 1}")  # move out 1.0mm

        time.sleep(1)

        self.cmd(f"G1 X{self.radius}")  # move out 1.0mm

        self.cmd(f"G02 I-{self.radius} J0 P{self.num_times}")

        self.cmd(f"G1 X{self.radius + 1}")  # move out 1.0mm

        time.sleep(1)

        # self.cmd("G53 G0 Z1")  # Move Z to the machine safe height offset by 1mm


if __name__ == "__main__":
    checker = BallbarCheck()

    mode = sys.argv[1]

    if mode == "prep":
        checker.prep_run()
    elif mode == "run":
        checker.do_run()
    else:
        print(f"error. mode was {mode}")
