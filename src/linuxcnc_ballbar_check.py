from __future__ import annotations

import sys

import linuxcnc


class BallbarCheck(object):
    def __init__(self) -> None:
        super().__init__()
        self.stat = linuxcnc.stat()
        self.command = linuxcnc.command()

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

    def run(self) -> None:
        radius = 100  # in mm
        goto_feed = 1000  # goto position feed
        operation_feed = 6000  # operation feed
        num_times = 1  # number of times to run it

        self.command.mode(linuxcnc.MODE_MDI)
        self.command.wait_complete()  # wait until mode switch executed

        self.cmd("G17")  # Select the XY plane
        self.cmd("G90")  # Absolute distance mode

        self.cmd("G53 G0 Z1")  # Move Z to the machine safe height offset by 1mm
        self.cmd("G54")  # select the G54 coordinate system
        self.cmd(f"G0 X{radius} Y0")  # Move in the XY plane to the starting position
        self.cmd(f"G1 Z0 F{goto_feed}")

        # Tell the operator to connect the ballbar

        # We set the feed that we'll be operating the rotation.
        # We might set this to other speeds depending on what we are measuring
        self.cmd(f"G1 F{operation_feed}")

        # Initiate the circular motion
        self.cmd(f"G03 I-{radius} J0 P{num_times}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        checker = BallbarCheck()
        checker.run()
    else:
        print("Usage: python ballbar_check.py run")
