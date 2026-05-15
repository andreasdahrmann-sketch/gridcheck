import ProjectDetailWorkspace from "@/components/projects/ProjectDetailWorkspace";

export default function Page({ params }: { params: { id: string } }) {
  return <ProjectDetailWorkspace projectId={params.id} />;
}
