from caremate_v4.tools.stt_tool import STTTool


def test_stt():

    # initialize tool
    stt_tool = STTTool()

    # path to test audio file
    audio_file = "generated_audio/4954a3d6-6e47-4971-a710-2b3ac369ab94.mp3"

    print("🎤 Testing STT Tool...")
    print(f"📂 Audio file: {audio_file}")

    # run transcription
    result = stt_tool.run(audio_file)

    print("\n✅ Transcription Result:")
    print(result)


if __name__ == "__main__":
    test_stt()