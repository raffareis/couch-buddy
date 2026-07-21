namespace BpBinReader;
public class TypeSchema(string name, string fullName, IReadOnlyList<FieldSchema> serializedFields, Type type, Guid typeId) {
    public string FullName { get; } = fullName;
    public string Name { get; } = name;
    public IReadOnlyList<FieldSchema> SerializedFields { get; } = serializedFields;
    public Type Type { get; } = type;
    public Guid TypeId = typeId;
}
