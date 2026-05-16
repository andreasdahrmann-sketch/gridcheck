import { redirect } from "next/navigation";

/** Legacy-Route: einheitlicher Projektierer-Einstieg unter /projektierer. */
export default function CheckPage() {
  redirect("/projektierer");
}
