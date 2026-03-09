import { render, screen } from "@testing-library/react";

import App from "./App";


it("shows filtered jobs tab by default", () => {
  render(<App />);

  expect(screen.getByRole("button", { name: "通过岗位" })).toBeInTheDocument();
});
