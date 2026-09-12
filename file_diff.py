"""텍스트 파일의 줄 단위 차이를 계산하는 기능."""

from pathlib import Path

from errors import MiniGitError


def line_diff(file1: str, file2: str) -> str:
    """LCS 기반의 간단한 줄 단위 차이를 반환한다(선택 보너스 명령)."""

    try:
        left = Path(file1).read_text(encoding="utf-8").splitlines()
        right = Path(file2).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError, ValueError) as error:
        raise MiniGitError(f"Cannot read file: {error}") from error

    rows = len(left) + 1
    columns = len(right) + 1
    lengths = [[0] * columns for _ in range(rows)]
    for left_index in range(len(left) - 1, -1, -1):
        for right_index in range(len(right) - 1, -1, -1):
            if left[left_index] == right[right_index]:
                lengths[left_index][right_index] = (
                    lengths[left_index + 1][right_index + 1] + 1
                )
            else:
                lengths[left_index][right_index] = max(
                    lengths[left_index + 1][right_index],
                    lengths[left_index][right_index + 1],
                )

    output: list[str] = []
    left_index = 0
    right_index = 0
    while left_index < len(left) and right_index < len(right):
        if left[left_index] == right[right_index]:
            output.append(f"  {left[left_index]}")
            left_index += 1
            right_index += 1
        elif (
            lengths[left_index + 1][right_index]
            >= lengths[left_index][right_index + 1]
        ):
            output.append(f"- {left[left_index]}")
            left_index += 1
        else:
            output.append(f"+ {right[right_index]}")
            right_index += 1
    while left_index < len(left):
        output.append(f"- {left[left_index]}")
        left_index += 1
    while right_index < len(right):
        output.append(f"+ {right[right_index]}")
        right_index += 1
    return "\n".join(output) if output else "No differences."
