import type { RevAlignment } from './types';

type AlignmentAxis = 'x' | 'y';

export function toAlignmentAttributes(
    axis: AlignmentAxis,
    alignment?: RevAlignment
): Record<string, string> {
    if (!alignment) return {};

    return {
        [`data-rev-align-${axis}`]: alignment,
    };
}
