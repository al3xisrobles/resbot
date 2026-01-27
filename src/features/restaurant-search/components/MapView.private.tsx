import React, { useMemo, useCallback } from "react";
import { MapPin } from "lucide-react";
import {
    Map,
    MapTileLayer,
    MapMarker,
    MapPopup,
    MapTooltip,
    MapZoomControl,
    MapLocateControl,
} from "@/components/ui/map";
import { Map as LeafletMap, Marker as LeafletMarkerType } from "leaflet";
import { Button } from "@/components/ui/button";
import type { SearchResult } from "@/lib/interfaces";

interface MapViewProps {
    searchResults: SearchResult[];
    mapCenter: [number, number];
    mapRef: React.RefObject<LeafletMap | null>;
    markerRefsMap: React.RefObject<Map<string, LeafletMarkerType>>;
}

export const MapView = React.memo(function MapView({
    searchResults,
    mapCenter,
    mapRef,
    markerRefsMap,
}: MapViewProps) {
    const venuePositions = useMemo(() => {
        const positions: Record<string, [number, number]> = {};
        searchResults.forEach((result) => {
            if (result.latitude != null && result.longitude != null) {
                positions[result.id] = [result.latitude, result.longitude];
            }
        });
        return positions;
    }, [searchResults]);

    const setMarkerRef = useCallback(
        (id: string, marker: LeafletMarkerType | null) => {
            if (marker) {
                markerRefsMap.current.set(id, marker);
            } else {
                markerRefsMap.current.delete(id);
            }
        },
        [markerRefsMap]
    );

    return (
        <Map center={mapCenter} zoom={13} className="h-full w-full" ref={mapRef}>
            <MapTileLayer />
            {searchResults.map((result) => {
                const position = venuePositions[result.id];

                if (!position) return null;

                return (
                    <MapMarker
                        key={result.id}
                        position={position}
                        ref={(marker: LeafletMarkerType | null) =>
                            setMarkerRef(result.id, marker)
                        }
                        icon={<MapPin className="size-6 text-black fill-black" />}
                    >
                        <MapTooltip side="top">
                            <div className="font-medium">{result.name}</div>
                            {result.neighborhood && (
                                <div className="text-xs text-muted-foreground">
                                    {result.neighborhood}
                                </div>
                            )}
                        </MapTooltip>
                        <MapPopup>
                            <div className="flex flex-col gap-2 items-start">
                                <div className="font-semibold text-lg">{result.name}</div>
                                {result.neighborhood && (
                                    <div className="text-sm text-muted-foreground">
                                        {result.neighborhood}
                                    </div>
                                )}
                                <Button
                                    size="sm"
                                    onClick={() =>
                                        window.open(`/venue?id=${result.id}`, "_blank")
                                    }
                                >
                                    Reserve
                                </Button>
                            </div>
                        </MapPopup>
                    </MapMarker>
                );
            })}
            <MapZoomControl className="top-auto left-1 bottom-2 right-auto" />
            <MapLocateControl className="top-auto right-1 bottom-2 left-auto" />
        </Map>
    );
});
