type FormState = {
  action: string;
};

export function FormActionBinding({ form }: { form: FormState }) {
  return <span>{form.action}</span>;
}
