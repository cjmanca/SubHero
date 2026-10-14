"""Stub for ffsubsync CLI in tests: shifts all input cues by --offset-ms."""

import argparse
import sys

import pysubs2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offset-ms", type=int, required=True)
    parser.add_argument("reference", nargs="?", default=None)
    parser.add_argument("-i", "--srtin")
    parser.add_argument("-o", "--srtout")
    parser.add_argument("--log-dir-path", default=None)
    args = parser.parse_args()
    doc = pysubs2.SSAFile.load(args.srtin, format="srt")
    out = pysubs2.SSAFile()
    for ev in doc.events:
        out.events.append(
            pysubs2.SSAEvent(
                start=ev.start + args.offset_ms,
                end=ev.end + args.offset_ms,
                text=ev.text,
            )
        )
    out.save(args.srtout, format="srt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
