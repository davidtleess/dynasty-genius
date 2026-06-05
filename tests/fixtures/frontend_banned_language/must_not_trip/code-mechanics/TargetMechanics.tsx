export function TargetMechanics() {
  return (
    <form action="/search" target="_blank">
      <input onChange={(event) => console.log(event.target.value)} />
    </form>
  );
}
