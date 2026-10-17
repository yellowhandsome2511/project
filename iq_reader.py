"""读取 IQ 数据，返回一维 NumPy 复数数组。

支持两种文件：
1. .npy：一维复数数组，或形状为 (N, 2) 的 I/Q 数组。
2. 原始二进制：按 I0, Q0, I1, Q1 ... 交织存储的 int8、int16、
   float32 或 float64 数据。原始文件必须指定 sample_type。

示例：
    python iq_reader.py samples.npy
    python iq_reader.py samples.bin --sample-type int16 --normalize
    python iq_reader.py samples.iq --sample-type float32 --skip 1000 --count 4096
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np


SAMPLE_TYPES = {
    "int8": np.dtype("i1"),
    "int16": np.dtype("i2"),
    "float32": np.dtype("f4"),
    "float64": np.dtype("f8"),
}


def read_iq(
    path: str | Path,
    *,
    sample_type: str | None = None,
    byte_order: str = "little",
    normalize: bool = False,
    skip: int = 0,
    count: int | None = None,
) -> np.ndarray:
    """读取 IQ 采样点。

    ``skip`` 和 ``count`` 的单位都是复数采样点，不是 I/Q 标量。
    ``normalize=True`` 只适用于整数 I/Q，将 int8/int16 除以 128/32768。
    浮点输入保持文件中的数值，不进行自动缩放。
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"找不到 IQ 文件：{file_path}")
    if skip < 0 or count is not None and count < 0:
        raise ValueError("skip 和 count 不能为负数")
    if byte_order not in ("little", "big"):
        raise ValueError("byte_order 只能是 'little' 或 'big'")

    if file_path.suffix.lower() == ".npy":
        if sample_type is not None:
            raise ValueError(".npy 文件自带数据类型，不需要 sample_type")
        if normalize:
            raise ValueError(".npy 文件不自动归一化；请按实际编码自行缩放")
        data = np.load(file_path, allow_pickle=False)
        if data.ndim == 1 and np.issubdtype(data.dtype, np.complexfloating):
            iq = data
        elif data.ndim == 2 and data.shape[1] == 2 and np.issubdtype(
            data.dtype, np.number
        ) and not np.issubdtype(data.dtype, np.complexfloating):
            real_dtype = np.float64 if data.dtype.itemsize > 4 else np.float32
            iq = data[:, 0].astype(real_dtype) + 1j * data[:, 1].astype(real_dtype)
        else:
            raise ValueError(".npy 内容必须是一维复数数组或 N×2 的数值型 I/Q 数组")
        return iq[skip : None if count is None else skip + count]

    if sample_type not in SAMPLE_TYPES:
        raise ValueError(
            "原始二进制文件需要 sample_type：int8、int16、float32 或 float64"
        )
    dtype = SAMPLE_TYPES[sample_type]
    is_integer = np.issubdtype(dtype, np.integer)
    if normalize and not is_integer:
        raise ValueError("normalize 只适用于 int8 和 int16")
    if dtype.itemsize > 1:
        dtype = dtype.newbyteorder("<" if byte_order == "little" else ">")

    bytes_per_sample = 2 * dtype.itemsize
    file_size = file_path.stat().st_size
    if file_size % bytes_per_sample:
        raise ValueError("文件长度不是完整 I/Q 采样点的整数倍；请检查数据类型")
    total_samples = file_size // bytes_per_sample
    if skip > total_samples:
        raise ValueError(f"skip={skip} 超过文件中的 {total_samples} 个采样点")
    samples_to_read = total_samples - skip if count is None else min(count, total_samples - skip)
    with file_path.open("rb") as stream:
        stream.seek(skip * bytes_per_sample)
        values = np.fromfile(stream, dtype=dtype, count=2 * samples_to_read)

    real_dtype = np.float64 if sample_type == "float64" else np.float32
    i = values[0::2].astype(real_dtype)
    q = values[1::2].astype(real_dtype)
    if normalize:
        scale = float(np.iinfo(dtype).max) + 1.0
        i /= scale
        q /= scale
    return i + 1j * q


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="IQ 文件路径（.npy 或原始二进制）")
    parser.add_argument("--sample-type", choices=SAMPLE_TYPES, help="原始文件的 I/Q 标量类型")
    parser.add_argument("--byte-order", choices=("little", "big"), default="little")
    parser.add_argument("--normalize", action="store_true", help="将整数 I/Q 归一化到约 [-1, 1)")
    parser.add_argument("--skip", type=int, default=0, help="跳过的复数采样点数")
    parser.add_argument("--count", type=int, help="最多读取的复数采样点数")
    args = parser.parse_args()

    try:
        iq = read_iq(
            args.path,
            sample_type=args.sample_type,
            byte_order=args.byte_order,
            normalize=args.normalize,
            skip=args.skip,
            count=args.count,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"采样点数：{len(iq)}；数组类型：{iq.dtype}")
    print(f"前 5 个采样点：{iq[:5]}")


if __name__ == "__main__":
    main()
