import React, { forwardRef } from 'react';
import type { LayoutProps, RevProps, RevGap, RevAlignment } from './types';
import { toSpacingAttributes } from './spacing';
import { toAlignmentAttributes } from './alignment';
import { cn } from '@/lib/utils';
import './Group.css';

export interface GroupProps extends LayoutProps {
    itemsSpacing?: RevGap;
    itemsAlignX?: RevAlignment;
    itemsAlignY?: RevAlignment;
    noWrap?: boolean;
    id?: string;
}

type GroupComponent = React.ForwardRefExoticComponent<
    GroupProps & React.RefAttributes<HTMLDivElement>
> & {
    Item: React.FC<GroupItemProps>;
};

export const Group = forwardRef<HTMLDivElement, GroupProps>(
    (
        {
            children,
            className,
            ariaLabel,
            id,
            itemsSpacing = 4,
            margin,
            padding,
            itemsAlignX = 'space-between',
            itemsAlignY = 'center',
            noWrap = false,
            isScrollable,
            isPositionContainer,
        }: GroupProps,
        ref,
    ) => {
        return (
            <div
                ref={ref}
                data-rev-component='group'
                className={cn('group', className)}
                aria-label={ariaLabel}
                id={id}
                data-rev-no-wrap={noWrap ? 'true' : 'false'}
                data-rev-scrollable={isScrollable}
                data-rev-position-container={isPositionContainer}
                {...toSpacingAttributes('m', margin)}
                {...toSpacingAttributes('p', padding)}
                {...toSpacingAttributes('g', itemsSpacing)}
                {...toAlignmentAttributes('x', itemsAlignX)}
                {...toAlignmentAttributes('y', itemsAlignY)}>
                {children}
            </div>
        );
    },
) as GroupComponent;

Group.displayName = 'Group';

export interface GroupItemProps extends RevProps {
    /** Flex-grow value for this item */
    grow?: 0 | 1 | 2 | 3 | 4 | 5 | boolean;
    children?: React.ReactNode;
}

const GroupItem = ({ className, ariaLabel, grow, children }: GroupItemProps) => {
    const flexGrow = grow === true ? 1 : typeof grow === 'number' ? grow : undefined;

    return (
        <div
            data-rev-component='group-item'
            className={cn('group-item', className)}
            aria-label={ariaLabel}
            data-rev-grow={flexGrow}>
            {children}
        </div>
    );
};
Group.Item = GroupItem;
