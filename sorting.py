"""내장 정렬 API에 의존하지 않는 정렬 기능."""

from typing import Any, Callable, Iterable, TypeVar


T = TypeVar("T")


def merge_sort(
    items: Iterable[T], key: Callable[[T], Any] = lambda item: item
) -> list[T]:
    """*items*를 안정 병합 정렬한 복사본을 O(n log n)에 반환한다.

    Python 내장 정렬 API를 사용하지 않고 직접 구현한다. 키가 같으면 왼쪽
    원소를 먼저 선택하므로 정렬 결과의 기존 순서가 유지된다.
    """

    values = list(items)
    if len(values) <= 1:
        return values

    middle = len(values) // 2
    left = merge_sort(values[:middle], key)
    right = merge_sort(values[middle:], key)
    merged: list[T] = []
    left_index = 0
    right_index = 0

    while left_index < len(left) and right_index < len(right):
        if key(left[left_index]) <= key(right[right_index]):
            merged.append(left[left_index])
            left_index += 1
        else:
            merged.append(right[right_index])
            right_index += 1

    merged.extend(left[left_index:])
    merged.extend(right[right_index:])
    return merged
