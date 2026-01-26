// Layout component types

export type RevGap = 0 | 4 | 8 | 12 | 16 | 20 | 24 | 32 | 40 | 48 | 56 | 64 | 80;

export type RevSpacing = RevGap | { top?: RevGap; right?: RevGap; bottom?: RevGap; left?: RevGap; x?: RevGap; y?: RevGap; all?: RevGap };

export type RevAlignment =
    | 'start'
    | 'center'
    | 'end'
    | 'stretch'
    | 'space-between'
    | 'space-around'
    | 'space-evenly';

export interface RevProps {
    className?: string;
    ariaLabel?: string;
}

export interface LayoutProps extends RevProps {
    margin?: RevSpacing;
    padding?: RevSpacing;
    isScrollable?: boolean | 'x' | 'y';
    isPositionContainer?: boolean;
    children?: React.ReactNode;
}
