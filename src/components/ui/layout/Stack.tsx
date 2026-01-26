import React, { forwardRef } from 'react';
import type { LayoutProps, RevGap, RevAlignment } from './types';
import { toSpacingAttributes } from './spacing';
import { toAlignmentAttributes } from './alignment';
import { cn } from '@/lib/utils';
import './Stack.css';

interface StackProps extends LayoutProps {
    itemsSpacing?: RevGap;
    itemsAlignX?: RevAlignment;
    itemsAlignY?: RevAlignment;
    tag?: 'div' | 'ul' | 'ol';
    isFullHeight?: boolean;
    id?: string;
}

export const Stack = forwardRef<HTMLDivElement | HTMLUListElement | HTMLOListElement, StackProps>(
    (
        {
            children,
            className,
            ariaLabel,
            id,
            margin,
            padding,
            itemsSpacing,
            itemsAlignX,
            itemsAlignY,
            tag,
            isScrollable,
            isPositionContainer,
            isFullHeight,
        }: StackProps,
        ref,
    ) => {
        const Component = (tag || 'div') as React.ElementType;

        return (
            <Component
                ref={ref}
                data-rev-component='stack'
                className={cn('stack', className)}
                id={id}
                aria-label={ariaLabel}
                data-rev-scrollable={isScrollable}
                data-rev-position-container={isPositionContainer}
                data-rev-full-height={isFullHeight}
                {...toSpacingAttributes('m', margin)}
                {...toSpacingAttributes('p', padding)}
                {...toSpacingAttributes('g', itemsSpacing)}
                {...toAlignmentAttributes('x', itemsAlignX)}
                {...toAlignmentAttributes('y', itemsAlignY)}>
                {children}
            </Component>
        );
    },
);

Stack.displayName = 'Stack';
