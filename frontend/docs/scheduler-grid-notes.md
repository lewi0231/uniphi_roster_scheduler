# Scheduler Availability Grid Notes

This layout renders a matrix of rotated day headings above worker availability checkboxes. Two small details made the alignment work reliably:

## Key Takeaways

- **Share a column template**  
  Both the header row and worker rows use the same CSS `grid-template-columns`. That guarantees the headings sit over the correct checkbox column.

- **Rotate only the inner element**  
  The grid cell stays unrotated (`display: flex; justify-content: center; align-items: center;`), and a child `<span>` is rotated with `-rotate-90`. This keeps the cell width consistent while still rendering vertical text.

- **Use `origin-center` when rotating**  
  Setting `transform-origin` to center prevents the rotated label from drifting left/right and keeps it centered above the checkbox column.

- **Constrain the rotated label's width**  
  Applying a fixed width (e.g. Tailwind `w-16`) forces the label text to break consistently, so each heading aligns vertically with its column.

Together, these tweaks ensure the header labels align with the underlying checkboxes, even with rotated text.
