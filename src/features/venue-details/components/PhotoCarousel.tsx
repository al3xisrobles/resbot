import { useState, useEffect } from "react";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
  type CarouselApi,
} from "@/components/ui/carousel";
import { cn } from "@/lib/utils";
import type { VenueData } from "../lib/types";

interface PhotoCarouselProps {
  venueData: VenueData;
  venueId: string;
}

export function PhotoCarousel({ venueData, venueId }: PhotoCarouselProps) {
  const [carouselApi, setCarouselApi] = useState<CarouselApi | null>(null);
  const [currentSlide, setCurrentSlide] = useState(0);

  useEffect(() => {
    if (!carouselApi) return;

    const onSelect = () => {
      setCurrentSlide(carouselApi.selectedScrollSnap());
    };

    onSelect();
    carouselApi.on("select", onSelect);
    return () => {
      carouselApi.off("select", onSelect);
    };
  }, [carouselApi]);

  if (!venueData.photoUrls || venueData.photoUrls.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>No photos available</p>
      </div>
    );
  }

  return (
    <div className="relative rounded-lg overflow-hidden cursor-pointer">
      <Carousel
        className="w-full z-9 rounded-lg overflow-hidden"
        setApi={setCarouselApi}
        opts={{ loop: true }}
      >
        <CarouselContent>
          {venueData.photoUrls.map((photoUrl: string, index: number) => (
            <CarouselItem key={`${venueId}-${index}-${photoUrl}`}>
              <div className="rounded-lg overflow-hidden border shadow-sm">
                <img
                  src={photoUrl}
                  alt={`${venueData.name || "Restaurant"} - Photo ${index + 1}`}
                  className="w-full h-[400px] max-w-full object-cover pointer-events-none select-none"
                  onError={(e) => {
                    const container = e.currentTarget.closest('.rounded-lg');
                    if (container) {
                      (container as HTMLElement).style.display = "none";
                    }
                  }}
                  loading="lazy"
                />
              </div>
            </CarouselItem>
          ))}
        </CarouselContent>
        <CarouselPrevious className="left-2" />
        <CarouselNext className="right-2" />
      </Carousel>

      <div className="absolute left-1/2 bottom-3 -translate-x-1/2 z-10">
        <div className="flex items-center gap-2 rounded-full bg-background px-3 py-1 shadow-sm">
          {venueData.photoUrls.map((_, index: number) => (
            <button
              key={index}
              type="button"
              onClick={() => carouselApi?.scrollTo(index)}
              className={cn(
                "h-2 w-2 rounded-full transition",
                currentSlide === index ? "bg-black" : "bg-gray-400"
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
