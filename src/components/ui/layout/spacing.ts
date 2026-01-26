import type { RevSpacing } from './types';

type SpacingPrefix = 'm' | 'p' | 'g';

export function toSpacingAttributes(
    prefix: SpacingPrefix,
    spacing?: RevSpacing
): Record<string, string> {
    if (!spacing) return {};

    const attrs: Record<string, string> = {};

    if (typeof spacing === 'number') {
        attrs[`data-rev-spacing-${prefix}-all`] = spacing.toString();
    } else if (typeof spacing === 'object') {
        if (spacing.all !== undefined) {
            attrs[`data-rev-spacing-${prefix}-all`] = spacing.all.toString();
        }
        if (spacing.x !== undefined) {
            attrs[`data-rev-spacing-${prefix}-x`] = spacing.x.toString();
        }
        if (spacing.y !== undefined) {
            attrs[`data-rev-spacing-${prefix}-y`] = spacing.y.toString();
        }
        if (spacing.top !== undefined) {
            attrs[`data-rev-spacing-${prefix}-top`] = spacing.top.toString();
        }
        if (spacing.right !== undefined) {
            attrs[`data-rev-spacing-${prefix}-right`] = spacing.right.toString();
        }
        if (spacing.bottom !== undefined) {
            attrs[`data-rev-spacing-${prefix}-bottom`] = spacing.bottom.toString();
        }
        if (spacing.left !== undefined) {
            attrs[`data-rev-spacing-${prefix}-left`] = spacing.left.toString();
        }
    }

    return attrs;
}
