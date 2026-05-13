#!/usr/bin/env python3

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ENCODER_ARGS = {
    '.mp4': [
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
    ],
    '.webm': [
        '-c:v', 'libvpx-vp9',
        '-deadline', 'good',
        '-cpu-used', '4',
        '-row-mt', '1',
        '-pix_fmt', 'yuv420p',
    ],
    '.avi': [
        '-c:v', 'mjpeg',
        '-q:v', '4',
        '-pix_fmt', 'yuvj420p',
    ],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate a fake video file that fades from black to white.'
    )

    parser.add_argument(
        'output',
        help='Output file path ending in .mp4, .webm, or .avi',
    )

    parser.add_argument(
        '--duration',
        type=float,
        default=300,
        help='Video duration in seconds. Default: 300',
    )

    parser.add_argument(
        '--width',
        type=int,
        default=1280,
        help='Video width. Default: 1280',
    )

    parser.add_argument(
        '--height',
        type=int,
        default=720,
        help='Video height. Default: 720',
    )

    parser.add_argument(
        '--fps',
        type=int,
        default=30,
        help='Frames per second. Default: 30',
    )

    parser.add_argument(
        '--bitrate',
        default=None,
        help='Optional target bitrate, for example 2M or 800k. Useful for range request testing.',
    )

    parser.add_argument(
        '--keyframe-seconds',
        type=float,
        default=2,
        help='Force a keyframe every N seconds. Default: 2',
    )

    parser.add_argument(
        '--noise-strength',
        type=int,
        default=0,
        help='Optional noise from 0 to 100. Increases file size but makes the image less perfectly flat.',
    )

    parser.add_argument(
        '--ffmpeg',
        default='ffmpeg',
        help='ffmpeg executable path. Default: ffmpeg',
    )

    return parser.parse_args()


def validate_args(args):
    output = Path(args.output)
    suffix = output.suffix.lower()

    if suffix not in ENCODER_ARGS:
        raise ValueError('Output must end in .mp4, .webm, or .avi')

    if args.duration <= 0:
        raise ValueError('--duration must be greater than 0')

    if args.width <= 0 or args.height <= 0:
        raise ValueError('--width and --height must be greater than 0')

    if args.fps <= 0:
        raise ValueError('--fps must be greater than 0')

    if args.keyframe_seconds <= 0:
        raise ValueError('--keyframe-seconds must be greater than 0')

    if not 0 <= args.noise_strength <= 100:
        raise ValueError('--noise-strength must be between 0 and 100')

    if shutil.which(args.ffmpeg) is None:
        raise ValueError(f'Could not find ffmpeg executable: {args.ffmpeg}')

    return output, suffix


def build_filter(args):
    filters = [
        f'fade=t=in:st=0:d={args.duration}',
    ]

    if args.noise_strength > 0:
        filters.append(f'noise=alls={args.noise_strength}:allf=t+u')

    return ','.join(filters)


def main():
    args = parse_args()

    try:
        output, suffix = validate_args(args)
    except ValueError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)

    source = (
        f'color=c=white:'
        f's={args.width}x{args.height}:'
        f'r={args.fps}:'
        f'd={args.duration}'
    )

    cmd = [
        args.ffmpeg,
        '-y',
        '-hide_banner',
        '-f', 'lavfi',
        '-i', source,
        '-vf', build_filter(args),
        '-an',
        *ENCODER_ARGS[suffix],
    ]

    if args.bitrate:
        cmd.extend(['-b:v', args.bitrate])

    if args.keyframe_seconds:
        cmd.extend([
            '-force_key_frames',
            f'expr:gte(t,n_forced*{args.keyframe_seconds})',
        ])

    cmd.append(str(output))

    print('Running:')
    print(' '.join(cmd))

    result = subprocess.run(cmd)

    if result.returncode != 0:
        return result.returncode

    print(f'Wrote {output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
