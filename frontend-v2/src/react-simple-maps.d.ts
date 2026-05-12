declare module 'react-simple-maps' {
    import { ComponentType, ReactNode, CSSProperties } from 'react'

    interface ComposableMapProps {
        projection?: string
        projectionConfig?: {
            scale?: number
            center?: [number, number]
            rotate?: [number, number, number]
        }
        width?: number
        height?: number
        className?: string
        style?: CSSProperties
        children?: ReactNode
    }

    interface GeographiesProps {
        geography: string | object
        children: (args: { geographies: Geography[] }) => ReactNode
    }

    interface Geography {
        rsmKey: string
        properties: {
            name?: string
            [key: string]: unknown
        }
        [key: string]: unknown
    }

    interface GeographyProps {
        geography: Geography
        fill?: string
        stroke?: string
        strokeWidth?: number
        style?: {
            default?: CSSProperties
            hover?: CSSProperties
            pressed?: CSSProperties
        }
        onClick?: (geo: Geography) => void
        className?: string
    }

    export const ComposableMap: ComponentType<ComposableMapProps>
    export const Geographies: ComponentType<GeographiesProps>
    export const Geography: ComponentType<GeographyProps>
}
