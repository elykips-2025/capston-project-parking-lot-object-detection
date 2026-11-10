import { useEffect, useState } from "react";
import {
  createOrganisation,
  listOrganisations,
  type Organisation,
} from "../api/organisations";

type Props = {
  onSelect: (organisation: Organisation) => void;
};

export default function OrganisationSelector({ onSelect }: Props) {
  const [organisations, setOrganisations] = useState<Organisation[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    listOrganisations()
      .then((data) => {
        if (active) setOrganisations(data);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Unable to load organisations",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedName = name.trim();
    if (trimmedName.length < 2 || creating) return;

    setCreating(true);
    setError(null);

    try {
      const organisation = await createOrganisation(trimmedName);
      onSelect(organisation);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to create organisation",
      );
    } finally {
      setCreating(false);
    }
  }

  if (loading) {
    return (
      <main className="onboarding-screen">
        <p>Loading organisations...</p>
      </main>
    );
  }

  return (
    <main className="onboarding-screen">
      <section className="onboarding-panel">
        <h1>Select an organisation</h1>
        <p>Choose the organisation whose parking facilities you want to manage.</p>

        {error && <p role="alert">{error}</p>}

        {organisations.length > 0 && (
          <div className="organisation-list">
            {organisations.map((organisation) => (
              <button
                type="button"
                key={organisation.id}
                onClick={() => onSelect(organisation)}
              >
                {organisation.name}
              </button>
            ))}
          </div>
        )}

        <form onSubmit={handleCreate}>
          <h2>Create an organisation</h2>

          <label htmlFor="organisation-name">
            Organisation name
          </label>

          <input
            id="organisation-name"
            type="text"
            value={name}
            maxLength={200}
            minLength={2}
            required
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Coventry Parking Ltd"
          />

          <button
            type="submit"
            disabled={creating || name.trim().length < 2}
          >
            {creating ? "Creating..." : "Create organisation"}
          </button>
        </form>
      </section>
    </main>
  );
}
