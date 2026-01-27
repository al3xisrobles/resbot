import { useAtom } from "jotai";
import { cityAtom } from "@/atoms/cityAtom";
import { CITIES } from "@/lib/cities";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

export function CitySelector() {
    const [selectedCity, setSelectedCity] = useAtom(cityAtom);

    return (
        <Select value={selectedCity} onValueChange={setSelectedCity}>
            <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select city" />
            </SelectTrigger>
            <SelectContent>
                {Object.values(CITIES).map((city) => (
                    <SelectItem key={city.id} value={city.id}>
                        {city.name}
                    </SelectItem>
                ))}
            </SelectContent>
        </Select>
    );
}
