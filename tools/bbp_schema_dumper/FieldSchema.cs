namespace BpBinReader;
public class FieldSchema(string name, ValueSchema value) {
    public string Name { get; } = name;
    public ValueSchema Value { get; } = value;
}
